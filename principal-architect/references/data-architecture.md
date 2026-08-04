# Data architecture — boundaries, stores, and schema evolution

The triage table marks a **data-model change as architecturally significant** — this is
the method behind that row. The principal architect's data concerns are *structural*:
who owns which data, how it's stored, how schemas evolve without breaking consumers,
and where data flows. Field-level enterprise data modelling belongs to a data-architect
role (orientation: **DAMA-DMBOK**, 2nd ed. — data governance, modelling, quality,
metadata); here we keep the lean subset a system architect must get right.

**The anti-pattern this file exists to prevent:** the big detached ERD. A wall-chart
data model maintained apart from the code rots faster than any other artifact. Model
the **slice you are touching**, keep it in the SD next to the design it explains, and
**generate from the schema** (migrations, ORM models, `information_schema`, Avro/proto
files) wherever possible — same models-as-code stance as Structurizr for C4.

## 1. Ownership & boundaries — who writes this data?

Strategic DDD applies to data exactly as to behaviour (`structure.md` §1):

- **Every dataset has exactly one owning context.** One component writes it; everyone
  else gets it through a contract (API, events, replicated read model) — never by
  reaching into the owner's tables. A **shared writable database is the tightest
  coupling two systems can have**: it turns every schema change into a multi-team
  negotiation. Introducing or removing one is always an ADR.
- **Reference data vs transactional data.** Slow-changing reference data may be
  replicated/cached across contexts; transactional data stays with its owner.
- **Reporting/analytics reads** come off a replica, CDC stream, or exported read
  model — not the operational store's hot path. The seam between operational and
  analytical data is a boundary; treat crossing it as an integration
  (`interfaces.md`), with a contract and an owner.

State the owner in the SD (`affects:`/prose) so `grep` answers "who owns this table".

## 2. Storage selection — keyed to the quality drivers

Choose the store family from the `Q.xx` scenarios, not from familiarity. The governing
trade-off is consistency vs availability under partition (**CAP** — Brewer; proved by
Gilbert & Lynch 2002) and, absent partitions, consistency vs latency (**PACELC**,
Abadi 2012). Polyglot persistence is normal; every store added is an operational cost
(backup, upgrade, expertise) — that trade-off is the ADR's consequences section.

| Need (typical Q.xx) | Store family | The cost side |
|---|---|---|
| Transactional invariants, joins | relational | vertical-scaling pressure; schema migration discipline |
| Flexible/nested documents, per-entity access | document | cross-entity consistency is yours to build |
| Extreme write throughput / linear scale | wide-column | eventual consistency; query patterns fixed up front |
| Sub-ms lookups, ephemeral state | in-memory KV | durability limits; cache-invalidation burden |
| Relationship traversal as the primary query | graph | niche expertise; bulk-analytics mismatch |
| Append-only facts, audit, replay | event log / event store | projections to maintain; GDPR erasure needs crypto-shredding (`privacy.md`) |

## 3. Schema evolution — change without breakage

A schema is a **published interface** the moment anything outside the owning component
reads it (the triage table's "new/breaking published interface" row applies).

- **Expand–contract** (a.k.a. parallel change, Fowler): add the new
  shape → migrate readers/writers → remove the old shape, each step deployable and
  reversible. Never a big-bang rename on a live store.
- **Event/message schemas** get explicit compatibility rules — backward/forward
  compatibility enforced by a schema registry where one exists; Avro/Protobuf
  compatibility semantics are the reference model. The schema file is the contract —
  link it from the SD via `api-spec:` like any other interface (`interfaces.md`).
- **A breaking schema change is ADR-worthy**; a compatible expansion usually isn't
  (triage as *local*). Data **migrations** at scale (backfills, dual-writes) get a
  short transition plan — same As-Is → interim → To-Be discipline as
  `migration.md`, scaled down.

## 4. Views — how data appears in the docs

- **ER diagram** (mermaid `erDiagram`, crow's-foot) in the SD, scoped to the
  entities of the slice — attributes only where they carry the point (keys,
  discriminators). Snippet in `mermaid-guide.md`.
- **Entity lifecycle** (`stateDiagram-v2`) for any entity whose states drive
  behaviour (order, claim, subscription) — often the clearest spec of business rules
  in the system. Snippet in `mermaid-guide.md`.
- **Data flow** is already on the C4 edges: label them with the data/contract that
  moves (mermaid-guide rule). For regulated or personal data, where it flows and
  *resides* is the DPIA's job — the §8 table in HLD/SAD (`privacy.md`); don't
  duplicate it.

## 5. Enterprise altitude — when data is the landscape

At enterprise level, data is the **D** in TOGAF's BDAT (Phase C: Data Architecture) —
inventory of the major data assets, their systems of record, and the flows between
them; a capability-to-data matrix answers "which capability masters which data".
**Data mesh** (Dehghani: domain ownership, data as a product, self-serve platform,
federated computational governance) is the decentralised option when a central
platform team is the bottleneck — adopting or rejecting it is an enterprise/solution
ADR, argued against the org's actual scale, not fashion.

## Linkage

- **PRD**: retention, residency, volume/growth land as `Q.xx`/`C.xx` drivers.
- **SD**: the ER/lifecycle views, the owner, `api-spec:` for schema contracts.
- **HLD**: stores appear as containers (L2) with "what it holds"; §8 DPIA for
  personal data; §9 FinOps rows for storage cost.
- **ADR**: store selection, shared-store introduction/removal, breaking schema
  change, operational↔analytical seam design.
