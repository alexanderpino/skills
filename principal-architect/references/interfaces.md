# Interfaces & API contracts — the architecture's load-bearing surface

A system's **contracts** are where its architecture meets everyone else's. For a service, the
API *is* the most consulted architectural artifact — and for **existing software**, the
contract is often the only accurate, machine-readable description of behaviour. So treat
interfaces as first-class: capture them in a **contract spec**, link that spec from the design
docs, and verify it. Prose in `SD §4` describes an interface; the **spec is the source of
truth**.

## Capture the contract in the right machine-readable form
Use the standard for the interface style; reference it, don't re-type it in Markdown.

| Interface style | Contract format | Notes |
|---|---|---|
| HTTP / REST | **OpenAPI 3.1** (`openapi.yaml`) | the de-facto REST contract; lintable with Spectral |
| Event / async / messaging | **AsyncAPI 3.0** (`asyncapi.yaml`) | topics, channels, message schemas (Kafka/AMQP/MQTT) |
| RPC / service-to-service | **Protocol Buffers** (`*.proto`, gRPC) | typed, versioned, codegen |
| GraphQL | **SDL schema** (`schema.graphql`) | client-shaped reads |
| Data interchange | **JSON Schema / Avro / Protobuf** in a schema registry | one source of truth per entity |
| CLI / library | the signatures + a usage example | the public surface others depend on |

Recovering these from existing code is part of reverse engineering (`reverse-engineering.md`):
generate the OpenAPI/proto from the running service or the route definitions, then treat it as
the As-Is contract.

## Link the spec into the docs (don't duplicate it)
- **SD front-matter** carries `api-spec:` pointing at the contract file, e.g.
  `api-spec: ../../contracts/openapi.yaml`. `SD §4 (Interfaces & contracts)` then summarises
  the *shape and the rules that aren't in the schema* (idempotency, ordering, auth, error
  semantics, pagination, rate limits) — not a field-by-field restatement.
- **HLD/AD**: an interface is part of the **Context (VP-CTX)** and **Functional (VP-FUNC)**
  views — external interfaces appear on the C4 Context/Container diagrams; the contract is the
  detail behind the arrow.
- A repo with many services benefits from an **interface catalog** (one table: interface →
  style → spec file → owning container → consumers) in the docs index.

## Versioning & compatibility — the part prose forgets
Contracts are promises; breaking them breaks consumers. State the rules explicitly:
- **Semantic versioning** of the contract; **additive/backward-compatible** changes are minor,
  **breaking** changes are major and **architecturally significant → an ADR**.
- **Deprecation policy**: how long an old version is supported, how it's signalled (sunset
  headers, schema `deprecated:` flags).
- **Consumer-driven contracts (CDC)** with **Pact** (https://pact.io) where many consumers
  depend on a provider — the consumers' expectations become tests the provider must pass.

## Verify the contract (means of verification for `F.xx`)
- **Lint** the spec: Spectral for OpenAPI/AsyncAPI (the bundled `spectral.yaml` is the hook).
- **Contract tests** in CI: provider verification + consumer (Pact) tests; schema-compatibility
  checks in the registry (e.g. Avro/Protobuf backward-compatibility gates).
- **Drift check**: the live service's generated spec must match the committed one (the
  contract equivalent of the As-Is/To-Be SD reflexion check in `migration.md` §4).

## Linkage
- `F.xx` functional drivers are realised by named operations in the contract; the contract
  tests are their *means of verification* (ISO/IEC/IEEE 29148).
- A change to a published interface is **architecturally significant** (`significance.md`) and
  needs an **ADR** + a refreshed contract + a version bump.
- The interface contract is a `view component` (ISO 42010) realising the functional/context
  views in `AD.md`.
