# ADR 004 — Variables, bounded expressions, and embedded subgraphs

**Status:** accepted
**Date:** 2026-07-31

## Context

Terrain Studio has no reusable subgraph definition, variable table, conditional demand node, or safe
expression evaluator. `GAEA-GAP.md` verifies the product need (`MacroPort`, `Var`, `Math`, `Switch`,
`Route`, `Chokepoint`, `Edge`). Chapter 14 grounds pure versioned node types, stable instance IDs,
demand evaluation, Merkle-style cache dependencies, deterministic serialization, and fixed-iteration
subgraphs instead of graph cycles. It does not choose Terrain Studio's exact ownership, parser, or
import schema; this ADR does.

## Decision drivers

- Saved documents must remain self-contained and deterministic offline.
- Unselected Switch branches must not evaluate.
- Expressions must never execute JavaScript or access browser/global objects.
- Reusable instances must not leak mutable state or float silently to a changed definition.
- Import/version/hash conflicts must fail visibly rather than best-effort rewiring.

## Considered options

### Definition ownership

1. External mutable library references: small documents, but offline/reproducible evaluation depends on
   mutable external state.
2. Copy expanded node piles: self-contained, but loses reuse and upgrade identity.
3. Embedded versioned definitions with pinned instances — selected.

### Expression implementation

1. JavaScript `eval`/`new Function`: rejected for code execution and non-reviewable semantics.
2. General third-party expression language: larger dependency and broader attack surface than needed.
3. Owned tokenizer + Pratt parser over a closed grammar — selected.

### Import conflicts

1. Truncated hash suffix rewriting: compact but introduces avoidable collision policy.
2. Silent last-writer wins: corrupts identity and is rejected.
3. Full canonical SHA-256 comparison with explicit conflict — selected.

## Decision

### Variables and scope

A document owns a variable table keyed by stable UUID. Each variable declares scalar numeric kind,
unit-dimension vector, range/default, and value. Display names are labels and need not be unique.
Parameter bindings store variable IDs, never names.

A subgraph instance creates a lexical child scope. An instance override shadows only the referenced
variable ID; unresolved reads fall back to the parent document scope. Overrides never mutate the
embedded definition or sibling instances. Rename preserves references; delete fails while dependants
exist unless the user explicitly removes those bindings in the same undo transaction.

### Switch, Gate, Route, and Edge

Route/Chokepoint preserve bytes and descriptors exactly. Switch stores a stable branch ID; every
branch must be type/unit compatible before save and only the selected branch is demanded. Gate's
closed value is a typed descriptor value, not an untyped zero.

Edge accepts a `MaskField`, has an authored threshold in `[0,1]` with initial value `0.5`, and emits a
boundary mask plus signed distance in metres. The initial 0.5 is an accepted product convention for
splitting a normalized mask at its midpoint, not a physical constant. Boundary adjacency is D8 on
square and D6 on hex; ties at exactly the threshold are inside. Distance uses the working lattice's
world metric.

### Bounded Math language

The grammar contains numeric literals, variable IDs, parentheses, unary `+`/`-`, binary `+ - * /`,
and `abs`, `min`, `max`, `clamp`, `sqrt`, `sinDeg`, `cosDeg`, `tanDeg`. There is no property access,
assignment, user function, loop, I/O, global name, implicit coercion, `eval`, or `new Function`.

A variable reference token is exactly `@{xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx}`, where hex is
case-insensitive, `y` is `8|9|a|b`, and the stored UUID is canonical lowercase. The braces make UUID
hyphens unambiguous with subtraction: `@{...}-2` is a reference followed by minus and a literal.
Whitespace is permitted between tokens, never inside the UUID token. Bare identifiers are reserved
function names only. Fixtures cover a hyphenated UUID, adjacent subtraction, malformed braces, upper-
case canonicalization, and an unknown but syntactically valid UUID.

Dimensional rules are explicit:

- `+`, `-`, `min`, and `max` require equal dimensions and preserve them;
- `clamp(value,lo,hi)` requires all three dimensions equal and preserves them;
- multiplication/division add/subtract unit exponent vectors;
- `sqrt` requires every exponent to be even and halves them;
- trigonometric functions require degrees and return dimensionless values;
- division by zero and every non-finite result are errors.

Resource limits are accepted security budgets, not terrain constants: at most 512 UTF-16 code units,
32 AST levels, and 256 evaluated operator/function nodes. Inputs at each limit must parse/evaluate;
513/33/257 must fail with the corresponding resource error. These bounds cap serialized attack size,
recursive parser depth, and per-evaluation work while covering the intended scalar-control language.

### Definitions, versions, and identity

An embedded definition has stable UUID, positive integer version, canonical content, full SHA-256
content hash, typed MacroPorts, exposed variable IDs, and an internal DAG. Instances pin
`(definitionId, version, fullHash)`. A breaking port change creates a new version. Old instances never
float.

Canonicalization is RFC 8785 JSON Canonicalization Scheme (JCS) over the semantic definition object.
Only Unicode scalar-value strings and finite IEEE-754 binary64 numbers are accepted; lone surrogates,
NaN, and infinities are errors. Negative zero is normalized to positive zero before JCS. UI/editor
layout fields are excluded from the semantic object. Same ID/version/hash deduplicates on import. Same
ID/version with a different full hash is a visible conflict and the import stops; the user must import
as a new definition/version. No truncated hash is used as identity. Direct or indirect definition
recursion is rejected by DFS before ordinary cross-boundary graph-cycle validation.

Cache identity follows chapter 14 and ADR 002: definition full hash/version, instance overrides,
effective seed, relevant context/substrate version, demanded output/group, and upstream port keys.
Cached values are immutable; identical instances may share them, while differing overrides cannot.

## Consequences and gates

- Rename/save/reload preserves variable references by UUID.
- An unselected throwing branch records zero evaluations.
- Hostile names (`constructor`, `globalThis`, property syntax), depth/operation/source overflows,
  unknown IDs, incompatible units, and non-finite results fail with typed errors.
- Inline and subgraph instances produce equivalent outputs for the same graph/seed/context.
- Direct/indirect recursion and cross-boundary cycles fail before evaluation.
- Save/reload retains full hashes and exact topology. Missing or mismatched definitions fail visibly.
- Same ID/version/different hash import is an error; there is no automatic identity rewrite.
- Fixed canonical definition byte strings and SHA-256 vectors gate key ordering, `1`/`1.0`, exponent
   spelling, negative zero, escaped Unicode, and layout-field exclusion.

The costs are a document schema extension and an intentionally small expression language. The gains
are offline reproducibility, bounded attack surface, deterministic cache identity, and reusable graphs
without mutable external dependencies.
