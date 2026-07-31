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

Use a maintained parser or a small allowlisted grammar selected in the architecture decision. Parse
to AST; allow only documented arithmetic/functions/constants; cap expression length, AST depth, and
operation count; reject non-finite values and unit-incompatible operations. No property access,
assignment, loops, I/O, globals, `eval`, or `new Function`.

**Acceptance gate** — `tests/legacy/_verify_math.js`: analytic expressions match expected float
results; same inputs are bit-identical; malformed syntax, division by zero/non-finite output,
unknown variables, incompatible units, and adversarial property/function expressions fail with
specific errors. A fixture attempting `constructor`/global access is the armed security failure.

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

Content/cache identity includes definition version, instance overrides, context, and upstream port
keys. Saved documents include referenced definitions or stable library references with hashes.
Copy/paste/import resolves ID collisions deterministically. Missing definitions and incompatible
versions fail visibly; migrations are explicit, never best-effort rewiring.

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
