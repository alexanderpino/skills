# Enterprise Architecture Bingo & Anti-Over-Engineering Matrix

The Enterprise Architecture Bingo Card serves as both a cultural mirror and an **adversarial auditing heuristic** for Principal Architects. When evaluating Architecture Design Records (ADRs), High-Level Designs (HLDs), or modernization proposals, use this matrix to distinguish between genuine solutions to business invariants and cargo-cult over-engineering.

---

## 1. The Thematic 5×5 B-I-N-G-O Matrix

Each column represents an essential architectural dimension. The arrangement balances foundational domain separation, data pipelines, distributed systems resilience, client ingress, and operational evolution.

| B<br>**(Boundaries & Domain)** | I<br>**(Integration & Events)** | N<br>**(Networking & Resilience)** | G<br>**(Gateways & Ingress)** | O<br>**(Operations & Evolution)** |
| :---: | :---: | :---: | :---: | :---: |
| **Bounded Context**<br><br>Drawing explicit linguistic and logical boundaries within a domain where terms have unambiguous meanings. | **Event Sourcing**<br><br>Preserving state mutations as an append-only sequence of immutable domain events instead of overwriting table rows. | **Circuit Breaker**<br><br>Failing fast and isolating failing dependencies to prevent cascading thread and connection pool exhaustion. | **API Gateway**<br><br>Centralizing reverse-proxy routing, SSL termination, and cross-cutting security for microservice clusters. | **Strangler Fig Pattern**<br><br>Risk-averse legacy modernization by intercepting and routing specific endpoints to new services incrementally. |
| **Hexagonal Architecture**<br><br>Isolating core domain logic completely from frameworks, databases, and I/O devices via Ports & Adapters. | **Outbox Pattern**<br><br>Guaranteeing atomic dual-writes between the local database transaction and message broker without distributed 2PC. | **Saga Pattern**<br><br>Orchestrating multi-service business transactions across distributed boundaries using compensating actions. | **Backend for Frontend**<br><br>Building dedicated API surfaces tailored to specific client ergonomics (mobile, web) to prevent monolithic API sprawl. | **Blue/Green Deployment**<br><br>Eliminating deployment risk by switching live traffic instantaneously between two identical production environments. |
| **Anti-Corruption Layer**<br><br>A defensive translation boundary preventing legacy or third-party schemas from polluting a clean domain model. | **CQRS**<br><br>Physically or logically decoupling the mutation model (*commands*) from high-throughput read models (*queries*). | 🎁 **FREE SPACE**<br><br>**Conway's Law**<br><br>*(System designs inevitably mirror the communication structures of the organizations that build them).* | **Micro-Frontends**<br><br>Decomposing complex browser SPAs into independently deployable feature apps via Module Federation. | **Observability**<br><br>Instrumenting distributed traces, metrics, and structured logs to infer internal system states purely from external outputs. |
| **Modular Monolith**<br><br>Structuring a single deployable into strictly encapsulated modules via language-level boundaries before physical splitting. | **Event-Carried State**<br><br>Enriching event payloads with complete entity state to eliminate synchronous callback queries from downstream services. | **Eventual Consistency**<br><br>Consciously choosing availability over immediate consistency (*CAP theorem*) by accepting asynchronous sync delays. | **Rate Limiting**<br><br>Applying token-bucket backpressure at ingress boundaries to protect services against traffic spikes and noisy neighbors. | **Chaos Engineering**<br><br>Proactively injecting controlled failures (latency, node crashes) into production to verify resilience hypotheses empirically. |
| **Vertical Slicing**<br><br>Organizing code around end-to-end business features rather than technical layers (controllers, services, repositories). | **Idempotency**<br><br>Designing APIs and event handlers so duplicate deliveries or retries cause zero state corruption or repeated side-effects. | **Service Mesh**<br><br>Offloading network policies (mTLS, traffic shifting, distributed tracing) from application code to sidecar/node proxies. | **Zero Trust**<br><br>Enforcing explicit mutual authentication and least-privilege authorization on every single hop, assuming internal breach. | **Infrastructure as Code**<br><br>Declaring, testing, and automatically provisioning compute, networking, and cloud topologies in version-controlled Git repos. |

---

## 2. Adversarial Audit Methodology

When reviewing an HLD, SAD, or ADR, the Principal Architect must use this card to stress-test architectural intent.

### A. The Over-Engineering Index (Scorecard)
Count the number of bingo squares proposed in the design:
* **0 - 2 Squares:** **Pragmatic Engineering.** Baseline architecture focused on direct problem solving.
* **3 - 4 Squares:** **Enterprise Complexity.** Requires explicit trade-off justification and cost modeling in an ADR.
* **5+ Squares (or 3+ in a Single Column):** 🚨 **"BINGO!" (Over-Engineering Alarm).**
  * High risk of *Resume Driven Development (RDD)* and speculative future-proofing.
  * The architect has likely introduced accidental complexity exceeding the business's organizational capacity.
  * **Mandatory Action:** Trigger an immediate adversarial grill session. Every square must be justified against measured Non-Functional Requirements (NFRs).

### B. The Conway's Law Mandatory Veto (Center Square)
The center square is free because **Conway's Law is immutable**:
> *"Any organization that designs a system will produce a design whose structure is a copy of the organization's communication structure."*

**The Veto Rule:** If an architect proposes Microservices, Sagas, Event-Carried State Transfer, and Micro-Frontends, but the team consists of **fewer than 10 engineers managed by a single lead**, veto the architecture immediately. Distributed architectures require distributed, autonomous teams. For small teams, mandate a **Modular Monolith**.

---

## 3. Top 5 Cargo-Cult Traps: Justified vs. Over-Engineered

| Pattern | Legitimate Justification | Cargo-Cult Red Flag (Reject) |
| :--- | :--- | :--- |
| **Micro-Frontends** | Multiple autonomous, distributed frontend teams deploying independently on distinct release cadences to a massive portal. | Single team maintaining an admin portal using Webpack Module Federation, fighting shared React state and CSS collisions. |
| **Event Sourcing** | Audit-heavy financial ledgers, legal dispute tracing, or complex multi-actor collaboration with time-travel requirements. | Basic administrative CRUD (e.g. user profiles, employee status, leave requests) requiring event versioning and complex projections. |
| **Saga Pattern** | Autonomous microservices across different organizational departments executing a long-lived distributed business process without 2PC. | Two microservices owned by the same team needing consistent writes; should be a single database transaction in a modular monolith. |
| **Service Mesh** | Polyglot enterprise cluster (50+ services) needing uniform mTLS encryption, canary routing, and traffic mirroring. | Small cluster of 5-10 services where simple ingress reverse proxies and cloud-managed IAM roles suffice. |
| **CQRS** | Radically asymmetric read/write ratios (e.g. 100,000 reads per second vs 5 writes per second) or completely distinct read models. | Standard line-of-business app where the read model and write model mirror the exact same database tables. |
