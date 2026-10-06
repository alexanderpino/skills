# Migration & modernization — As-Is → To-Be

A grounded strategy for large system transformations: choosing a migration approach,
recovering the **As-Is** accurately, designing safe **transition states**, and applying the
right modernization/integration patterns so reliability holds *during* the move. Migration
is usually **solution** or **enterprise** altitude work and is documented in a dedicated
**Transition Architecture** (`transition-architecture.md`), which sits between the Baseline
(As-Is) and Target (To-Be) architectures — a TOGAF ADM Phase E/F concept.

## 1. Pick the migration strategy — the 7 R's

For each system/workload, classify the move with the industry-standard **7 R's** (AWS,
expanding Gartner's original 5 R's). Most portfolios use 3–5 of these across their apps.

| Strategy | What it means | Use when |
|---|---|---|
| **Retire** | decommission | the app is unused / superseded |
| **Retain** | keep as-is (revisit later) | not worth moving yet, or constrained |
| **Rehost** | lift-and-shift, no code change | speed/exit-datacenter; optimize later |
| **Relocate** | move at hypervisor/VM level | bulk move without rebuild (e.g. VMware→cloud) |
| **Replatform** | lift-tinker-shift (e.g. managed DB) | small cloud wins without re-architecting |
| **Repurchase** | replace with a (SaaS) product | a good COTS/SaaS alternative exists |
| **Refactor / re-architect** | rebuild for cloud-native | high value justifies deep change |

> Gartner's 5 R's were Rehost, Refactor, Revise, Rebuild, Replace; AWS added Retire (2016)
> and Retain (2017), and Relocate later. Reference: AWS Prescriptive Guidance, "The 7 Rs."

## 2. The four transformation scenarios (blueprints)

**A. Local-to-Global** — decentralised, locally-built systems → one central global platform.
- Forces: data sovereignty/residency, latency, divergent local data models, regional rules.
- Blueprint: define the **canonical global model** + a per-region **Anti-Corruption Layer**
  (§3) so local quirks don't pollute the platform; converge via **event-driven
  intermediaries** while regions cut over one at a time (**Strangler Fig**). Keep a single
  source of truth per entity; map local schemas/protocols to the global standard (§5).

**B. On-Premise → Cloud-native** — own datacenters → public/hybrid cloud.
- Forces: cost (FinOps), operational model change, networking, security boundary.
- Blueprint: classify each workload with the **7 R's**; usually rehost for speed, then
  replatform/refactor the high-value ones. Run **hybrid** during transition (a network
  bridge + identity federation), validate per workload, and use the FinOps cost matrix
  (HLD/SAD §9) as a go/no-go gate.

**C. Monolith → Distributed / SaaS** — split a legacy monolith or integrate SaaS.
- Forces: tangled data model, shared database, transactional coupling.
- Blueprint: **Strangler Fig** around the monolith; carve **bounded contexts** out one at a
  time behind an **ACL**; decouple with **event-driven intermediaries**; split the shared DB
  last (data is the hardest part — use CDC, §5). Repurchase capabilities that a SaaS does
  better.

**D. Platform exit — mainframe, proprietary Unix, end-of-support OS or hypervisor.**
- Forces: the platform still works, often very well, but skills are retiring, the cost
  model (mainframe capacity charges, licence changes) or vendor support no longer fits,
  and delivery is slow. Batch windows, JCL job chains, CICS/IMS transactions, EBCDIC and
  packed-decimal data, and undocumented operational knowledge carry most of the risk
  (`systems-architecture.md` §5).
- Blueprint: inventory **transactions and batch jobs**, not just programs, and recover
  their runtime behaviour (§4) before choosing. Then pick per workload: **API-enable in
  place** (expose transactions through an API layer and strangle from the outside);
  **rehost** onto an emulation or rehosting runtime (fast, keeps COBOL, keeps the skills
  problem); **refactor** with automated code conversion (keeps the logic, produces code
  nobody chose to write; budget for clean-up); or **rebuild/repurchase** per capability.
  Convert data with explicit encoding and numeric-format mapping (§5) and reconcile
  totals per batch run. Run old and new in **parallel** with output comparison before
  each cutover; the batch schedule is the cutover plan. The same blueprint applies to
  proprietary Unix (AIX, HP-UX, Solaris) and to VM estates leaving a hypervisor after a
  licensing change.

## 3. Modernization & integration patterns — when to use which

| Pattern | Purpose | Use when | Grounding |
|---|---|---|---|
| **Strangler Fig** | gradually replace a legacy system by routing slices to the new one until the old is "strangled" | you cannot do a big-bang cutover; want incremental, reversible steps | Martin Fowler, *StranglerFigApplication* (martinfowler.com); AWS/Azure migration patterns |
| **Anti-Corruption Layer (ACL)** | a translation layer so the legacy data model does not leak into / corrupt the new model | the legacy and target domain models differ; integrating with a system you don't control | Eric Evans, *Domain-Driven Design*; Azure Architecture Center — Anti-Corruption Layer pattern |
| **Event-Driven Intermediary** | decouple old and new via an event broker/queue so neither calls the other directly | you need temporal decoupling, buffering, or fan-out during coexistence | enterprise integration / event-driven architecture; broker e.g. Kafka |

A typical transition uses all three together: a façade/router (Strangler Fig) in front, an
ACL at each legacy boundary, and an event bus carrying changes between old and new while both
run in parallel.

```mermaid
flowchart LR
  client([Client]) --> router{Strangler<br/>router}
  router -->|migrated slices| newsys[New service]:::new
  router -->|not yet| legacy[Legacy monolith]:::old
  legacy <-->|events| bus[(Event bus)]:::mid
  newsys <-->|events| bus
  newsys --- acl[ACL]:::acl --- legacy
  classDef new fill:#d9ead3,stroke:#333
  classDef old fill:#f4cccc,stroke:#333
  classDef mid fill:#fff2cc,stroke:#333
  classDef acl fill:#cfe2f3,stroke:#333
```

## 4. Recover the As-Is from runtime (automated)

Static archaeology (`reverse-engineering.md`) shows *structure*; to capture true **runtime
behaviour** of an existing system, use **dynamic analysis** — it is preferred over static
analysis for behaviour because polymorphism and dynamic binding hide call paths in the
source. Turn observed runs into **As-Is sequence diagrams** (`SD.md`):

- **Distributed tracing** — instrument with **OpenTelemetry** (https://opentelemetry.io);
  spans across services *are* the message sequence. Trace backends (Jaeger, Zipkin, Grafana
  Tempo) and **APM** (Datadog, Dynatrace, New Relic) render service maps and traces you
  translate into a mermaid `sequenceDiagram`.
- **Log analysis** — correlate structured logs by request/correlation ID to reconstruct the
  call order when tracing isn't available.
- **Trim & merge** — collapse repeated traces and merge scenarios (k-tail/LTS merging) so the
  diagram shows distinct behaviours, not noise.

**Grounding (sequence-diagram recovery from traces):** Briand, Labiche & Leduc, "Toward the
Reverse Engineering of UML Sequence Diagrams for Distributed Java Software," *IEEE TSE*
32(9):642–663 (2006); Briand, Labiche & Miao, WCRE 2003; Delamare, Baudry & Le Traon (2006);
Ziadi et al., "A Fully Dynamic Approach…," ICECCS 2011. A key benefit they note: a
reverse-engineered (As-Is) sequence diagram can be **conformance-checked against the designed
(To-Be) one** — discrepancies reveal drift or defects (the behavioural twin of the reflexion
model in `reverse-engineering.md`).

Mark every recovered SD with `source: traced` (vs `source: designed`) — see `SD.md`.

## 5. Data & protocol mapping (legacy → modern standards)

The hardest part of any migration is data. Map deliberately, and prefer automation:

- **Protocol mapping** — legacy/proprietary protocols, SOAP, fixed-width/EDI, RPC → modern
  **REST** (resource CRUD), **GraphQL** (client-shaped reads), **gRPC** (typed, low-latency
  service-to-service), or **cloud-native event streams** (Kafka/Kinesis/PubSub). Put the
  translation in the **ACL** or an API gateway, never in the new domain core.
- **Schema mapping** — document old→new field/type mappings explicitly (a mapping table per
  entity); generate adapters from a schema registry (Avro/Protobuf/JSON-Schema) where
  possible; keep a single source of truth per entity.
- **Data movement** — use **Change Data Capture (CDC)** (e.g. Debezium) to stream changes
  from the legacy store to the new one so both stay consistent during coexistence, enabling a
  reversible cutover. Validate with reconciliation counts/checksums before each cutover.
- **File integrations** — replace local file drops/batch with event streams or object-storage
  events; keep an ACL adapter that still speaks the old format until producers migrate.

Record each significant mapping/CDC/protocol choice as an ADR; capture residual risks in the
Transition Architecture (§6) and the threat model (HLD/SAD §8).

## 6. Document it: the Transition Architecture

Use `transition-architecture.md`. It forces **Baseline (As-Is) → interim states (T1, T2 …) →
Target (To-Be)**, and for each interim state: scope, the patterns used (§3), a **risk
analysis**, **rollback strategy**, and **validation/exit criteria** before the next step. This
is TOGAF ADM Phase E (Opportunities & Solutions) / Phase F (Migration Planning): never jump
from As-Is to To-Be in one undocumented leap.

## 7. Platform lifecycle — the end-of-support register and the technology radar

Most migrations are not chosen; an end-of-support date forces them. Treat platform lifecycle
as a standing input to the roadmap rather than a surprise:

- **End-of-support register.** For every platform component (OS and kernel line, database
  engine, runtime, hypervisor, network OS, framework, managed-service version), record the
  version in use, the vendor's end of standard and extended support, and the owner. Each
  entry is a `C.xx` with a date. An entry within the planning horizon becomes a work package
  in the roadmap (TOGAF Phase E/F) or a Transition Architecture (§6). An entry past its date
  is a security finding in the threat model.
- **Technology radar.** Keep the organisation's technology choices in four rings, after
  Thoughtworks: **Adopt** (the default), **Trial** (use on real but contained work),
  **Assess** (explore with a spike), **Hold** (no new use; plan the exit). A move from Trial
  to Adopt, or from anything to Hold, is an enterprise-level ADR. The radar is how the
  "boring technology" rule (`anti_over_engineering.md`) and new technology coexist: new
  things enter through Assess and Trial with a named driver, instead of being either banned
  or adopted by fashion.
- **Domain specifics** — kernel and OS lifecycles, CPU-architecture moves, mainframe exits:
  `systems-architecture.md` §5; network transitions (IPv6, SD-WAN, post-quantum TLS):
  `network-architecture.md` §§5, 8; cloud estate evolution and exit obligations:
  `cloud-architecture.md` §§8, 10.
