# Sprint 8 — Graph machinery: flow control, variables, math, subgraphs `[E]`

**Goal.** Fix the workflow hole that caps graph size and reuse. Route/Edge ship first; conditional
flow relies on Sprint 2 demand-driven evaluation; variables and expressions are typed, scoped, safe,
and serializable; subgraphs become reusable versioned definitions rather than copied node piles.

**Depends on:** Sprint 2 typed ports, demand-driven evaluation, source-port edges, and document
versioning. **Maps to** `GAEA-GAP §Part 3 #4`. Gaea Utility family: 20 nodes, Terrain Studio currently
ships none.

**Architecture gate.** Before variables/subgraphs, decide lexical scope, definition ownership,
versioning, cache identity, recursion policy, and safe expression parser. Never use JavaScript `eval`
or `new Function`.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---|---|
| S8.1 | Route / Chokepoint / Edge | `[C]` | 3 | typed identity + boundary extraction; ship first |
| S8.2 | Switch / Gate conditional flow | `[E]` | 5 | lazy branch demand; typed branch compatibility |
| S8.3 | Typed graph variables + scope | `[E]` | 8 | stable IDs, units, undo/serialization, lexical subgraph override |
| S8.4 | Safe Math expression node | `[E]` | 5 | parsed AST, allowlist, limits, finite/unit validation |
| S8.5 | Versioned subgraph definitions + ports | `[E]` | 8 | reusable definitions, instances, instance parameters, no recursion |
| S8.6 | Subgraph caching, persistence, migration | `[E]` | 5 | content identity, independent instances, copy/import/version upgrade |

---

## Technical refinement

### Locked runtime contract — [ADR 004](../adr-004-graph-machinery.md)

- Variables and subgraph definitions are embedded
  in the saved document for this sprint; there is no mutable external library dependency. Importing
  a library item copies a canonical definition plus content hash into the document.
- Route/Chokepoint are typed identity nodes. Edge emits `boundaryMask:[0,1]` and
  `signedDistance:m`; threshold is authored in `[0,1]` with accepted initial value `0.5`, exact-threshold
  samples are inside, and the boundary uses D8 on square / D6 on hex while distance uses the lattice
  world metric.
- Switch selection is a persisted stable branch ID. All branch descriptors must be compatible before
  save/evaluation; only the selected branch is demanded. Gate's closed value is a typed constant
  declared by its descriptor, never an untyped zero.
- Variables live in a document table keyed by stable ID and carry scalar kind, unit-dimension vector,
  range/default, and value. Display names are non-unique labels. Subgraph instances form child scope:
  reads fall back to parent IDs, while instance overrides shadow only the referenced ID and never
  mutate the definition or siblings.
- Math uses an owned Pratt parser, not `eval`, `new Function`, or a general scripting dependency.
  Grammar allows numeric literals, variable tokens `@{uuid}`, parentheses, unary `+/-`, binary `+ - * /`, and
  `abs`, `min`, `max`, `clamp`, `sqrt`, `sinDeg`, `cosDeg`, `tanDeg`. ADR 004 defines each function's
  dimensional contract. Accepted security budgets are 512 UTF-16 code units, AST depth 32, and 256
  evaluated operator/function nodes; 513/33/257 are errors. No names other than resolved variable tokens
  and the allowlist exist.
- A subgraph definition has stable ID, positive integer version, content hash, typed MacroPorts,
  exposed variable IDs, and internal DAG. Instances pin `(definitionId, version, hash)`. Any port-
  breaking edit creates a new version; old instances do not float. Direct/indirect recursion is
  rejected by definition-reference DFS before graph cycle validation.
- Definitions use canonical full SHA-256 hashes. Same ID/version/hash deduplicates; same ID/version
  with a different full hash is a visible import conflict and no data is rewritten. Cache identity is
  the full definition hash/version, instance overrides, evaluation context/substrate version,
  effective seed, demanded output/group, and upstream port keys; cached values are immutable.

### Owning code surfaces and cut order

1. **R0:** freeze S2 port/cache/document contracts and arm malicious-expression,
   recursive-definition, missing-hash, and name-collision fixtures before implementation.
2. **S8.1:** land generic identities and Edge outputs; no variable/subgraph schema is needed.
3. **S8.2:** add lazy Switch/Gate using S2 demand propagation and source-port persistence.
4. **S8.3:** add document variable table, parameter bindings, invalidation index, inspector, undo,
   and serialization. Scope/override behavior is complete before Math consumes variables.
5. **S8.4:** implement tokenizer, Pratt parser, unit checker, bounded interpreter, and precise errors
   as separate modules under `src/core/`; the AST is serializable data, never executable source.
6. **S8.5–S8.6:** add embedded definitions/MacroPorts, then instances, cross-boundary cycle checks,
   cache keys, copy/import, and explicit version migration in that order.

### Verification matrix and Ready condition

| Contract risk | Passing endpoint | Mutation that must be red |
|---|---|---|
| Eager branch | unselected throwing branch is never demanded | evaluate all Switch inputs |
| Name identity | rename preserves stable references | name-keyed variable binding |
| Expression escape | bounded allowlist and unit-correct result | constructor/global/deep AST |
| Instance leakage | overrides independent; immutable cache share only | mutable result alias |
| Recursive graph | direct/indirect definitions rejected before run | self-containing definition |
| Import drift | exact dedupe or visible full-hash conflict | silent rename/overwrite |

Sprint 8 is Ready when Sprint 2 exits, ADR 004's schema fixtures load, and all four hostile
fixtures in R0 have been observed red. Loops and external shared libraries remain out of scope.

---

### S8.1 — Route / Chokepoint / Edge · `[C]` · 3 pts
**User story:** As a graph author, I can organize wires and extract mask boundaries without changing
values.

Route/Chokepoint are generic typed identities: output type/unit equals input. Edge accepts a scalar
mask and emits boundary mask/distance according to a fixed neighborhood contract.

**Acceptance gate** — `tests/legacy/_verify_flow_control.js`: Route/Chokepoint preserve typed value
bytes and metadata exactly for scalar and vector fixtures. Edge of an analytic disc is one legal-
neighbour ring at the declared threshold; a constant field is empty. Square/hex boundary location is
within one cell. A Route that drops source type/unit is the armed failure.

---

### S8.2 — Switch / Gate · `[E]` · 5 pts
**User story:** As a graph author, I can select a compatible branch without computing branches that
cannot affect the requested output.

Switch inputs must share value/semantic type and unit; Gate preserves type with a declared closed
value. Only the selected branch is demanded. Thumbnail policy may request branch previews explicitly,
but graph evaluation cannot eagerly execute all branches as today.

**Acceptance gate** — `tests/legacy/_verify_switch.js`: every branch returns exactly its selected
value; incompatible branches are rejected at connection time; an unselected fixture branch that
throws/records evaluation is never invoked. Changing selection invalidates Switch's downstream cone,
not unrelated branches. Save/reload/undo preserve selection and source ports.

---

### S8.3 — Typed variables + scope · `[E]` · 8 pts
**User story:** As a graph author, one named value can drive many compatible parameters, with local
subgraph overrides and deterministic serialization.

Variables have stable IDs separate from display names, scalar type, physical unit, default/range,
and graph scope. Subgraphs add lexical child scope; instance overrides never mutate the definition or
sibling instances. Rename preserves references; delete reports dependants. Variable edits are one
undo record and invalidate only dependent cones.

**Acceptance gate** — `tests/legacy/_verify_variables.js`: one variable drives three parameters and
updates exactly those cones; rename/save/reload preserves references by ID; incompatible units fail;
two subgraph instances with different overrides remain independent. A name-keyed fixture breaks on
rename and must fail.

---

### S8.4 — Safe Math · `[E]` · 5 pts
**User story:** As a graph author, I can derive scalar controls from variables using deterministic,
reviewable expressions without executing arbitrary code.

Use the locked owned Pratt grammar above. Parse to AST, enforce the stated source/depth/operation
limits, and reject non-finite values and unit-incompatible operations. No property access,
assignment, loops, I/O, globals, `eval`, or `new Function`.

**Acceptance gate** — `tests/legacy/_verify_math.js`: analytic expressions match expected float
results; same inputs are bit-identical; malformed syntax, division by zero/non-finite output,
unknown variables, incompatible units, and adversarial property/function expressions fail with
specific errors. A fixture attempting `constructor`/global access is the armed security failure.
Valid expressions at 512/32/256 pass; 513/33/257 fail; parse plus one evaluation at the maximum valid
budget completes without unbounded allocation or recursion. UUID-token fixtures cover adjacent minus,
case canonicalization, malformed braces, and unknown IDs.

---

### S8.5 — Versioned subgraph definitions + ports · `[E]` · 8 pts
**User story:** As a graph author, I can encapsulate a working chain once, expose typed ports and
parameters, and instantiate it repeatedly without duplicating internals.

A subgraph is a versioned definition with stable ID, typed MacroPorts, parameter surface, internal
DAG, and instances. Definitions cannot recursively contain themselves; graph-cycle validation spans
instance boundaries. Internal nodes are hidden in the parent view but editable in definition view.
Changing a definition is explicit and undoable; breaking port changes require a new version/migration.

**Acceptance gate** — `tests/legacy/_verify_subgraph.js`: a three-node definition instantiated twice
matches the equivalent inlined chain; typed ports reject incompatible wires; direct/indirect recursion
and cross-boundary cycles fail; internal nodes do not leak into parent selection/palette. Different
instance overrides produce independent results.

---

### S8.6 — Subgraph cache/persistence/migration · `[E]` · 5 pts
**User story:** As a graph author, reusable definitions survive save/share/import and cache safely
without instances leaking state into each other.

Content/cache identity includes full definition hash/version, instance overrides, context/substrate,
effective seed, demanded output/group, and upstream port keys. Saved documents embed referenced
definitions. Copy/paste/import deduplicates exact identity and rejects same-ID/version hash conflicts.
Missing definitions and incompatible versions fail visibly; migrations are
explicit, never best-effort rewiring.

**Acceptance gate** — `tests/legacy/_verify_subgraph_persistence.js`: save/reload and copy/import retain
exact output/topology; two identical instances may share immutable cached results while different
overrides never alias mutable state; changing a definition invalidates only its instances and their
downstream cones. Missing/wrong definition hash is the armed failure.

---

## Sprint 8 exit gate

- Flow-control, Switch, variable, Math security/unit, subgraph, and persistence gates are green with
  armed failing fixtures.
- Full digest is bit-identical across repeated runs with the same variables/definitions/root seed;
  skipped = 0.
- Old documents migrate, production build and built-bundle digest pass, and full sweep is green.

---

## Named follow-up

LoopBegin/LoopEnd becomes a fixed-iteration outer loop around a subgraph, never a graph cycle.
Wizard-style nodes become saved subgraph presets only after versioned encapsulation is stable.
