# Structure & patterns — finding boundaries, choosing structure, selecting tactics

`methods.md` tells you how to *derive* drivers, quality scenarios and decisions.
This file is the other half: once you know the drivers, **how do you choose the
shape?** It answers the question the rest of the skill assumes you can already
answer — *"what structure, and which patterns?"* — and it is deliberately a
**selection guide, not a catalogue to memorise**. Patterns are a means; the driver
is the end.

**Every claim here is grounded in a recognised standard or its originating body**, not
invented — full citations in §6 and `standards.md`. The ISO/IEC/IEEE backbone still
governs: a structure/tactic choice is an **architecture decision** (ISO/IEC/IEEE
42010:2022) recorded as an ADR, and the qualities a tactic serves are named in
**ISO/IEC 25010:2023**. The pattern-level content is grounded in **The Open Group**
(O-AA Standard — DDD strategic patterns + agile architecture), the **SEI** (tactics),
**Microsoft Azure Architecture Center** and **microservices.io** (cloud/distributed
patterns), and the named originating authors below.

**Read this for the trade-offs, not just the names.** Every option carries a cost as
well as a benefit; the tables give *when to use it* **and** *when not to / what it
costs*, because an architect who only knows the upside will reach for the wrong tool.

Two questions, two axes:

1. **Where are the boundaries, and what overall structure?** → strategic DDD +
   structuring patterns (§§1–2).
2. **Which tactic/pattern realises *this* quality scenario?** → the forward
   tactic catalogue (§3).

**The golden rule for both:** *derive the choice from a driver, pick from genuine
alternatives, and record it as an ADR.* Adopting or dropping a style or pattern
across more than one component is **architecturally significant** by definition
(`significance.md` item 7) — so it carries a `level:`-tagged ADR with the options
you weighed and what you traded. This file gives you the menu; `methods.md` §8
gives you the decision discipline.

---

## 1. Finding boundaries — strategic DDD

The skill repeatedly treats a *boundary* as the unit of architectural significance,
but a boundary is only as good as the line it's drawn on. **Strategic Domain-Driven
Design** — originated by Eric Evans (*Domain-Driven Design*, 2003), extended by Vaughn
Vernon (*Implementing DDD*), and now codified as a standard by **The Open Group** in its
**Open Agile Architecture (O-AA) Standard** ("DDD strategic patterns") — is the
recognised method for drawing it well. It maps directly onto artifacts this skill
already produces:

| DDD concept | What it is | Lands in this skill as |
|---|---|---|
| **Subdomain** | a distinct area of the problem | groups `F.xx` functional drivers; informs build/buy |
| **Bounded context** | a boundary inside which one model + one language holds | a container/component boundary (C4); the thing an ADR protects |
| **Ubiquitous language** | the agreed terms inside a context | `GLOSSARY.md` (per-context if they conflict) |
| **Context map** | how contexts relate | the relationships on the C4 Context/Container view |

**Classify subdomains — it decides where effort goes:**
- **Core** — your differentiator. Build it, design it carefully, spend your best
  people and most ADRs here.
- **Supporting** — necessary but not special. Build simply, or outsource.
- **Generic** — solved problems (auth, billing, notifications). **Buy/adopt**, don't
  build. (This is the honest input to a solution-level build-vs-buy ADR, `methods.md` §4.)

**Heuristics for *where* the boundary falls** (use several; they should agree):
- **Language shifts.** The same word means different things ("account", "order") →
  a context edge. A model that needs "context-qualified" terms is two models.
- **Rate of change.** Things that change together belong together (CCP, §2); a
  seam between fast- and slow-changing areas is a natural boundary.
- **Data ownership.** One context owns each piece of data; others get a copy or a
  query. Shared mutable tables across boundaries is the smell, not the design.
- **Consistency boundary.** What must be transactionally consistent stays inside one
  boundary (the **aggregate**, §2); what can be eventually consistent crosses it.
- **Team / Conway's Law.** Boundaries align to teams whether you plan it or not;
  design the boundaries you *want* and let teams follow (Inverse Conway Maneuver).

**Context-mapping relationships** — name the relationship on each boundary, because
it dictates coupling and who absorbs change:

| Relationship | Use when |
|---|---|
| **Partnership** | two contexts succeed/fail together; coordinate releases |
| **Customer–Supplier** | downstream has a voice in the upstream's roadmap |
| **Conformist** | downstream accepts the upstream model as-is (no leverage) |
| **Anti-Corruption Layer (ACL)** | you must translate to keep a foreign model out (see `migration.md`) |
| **Open Host Service + Published Language** | one context serves many → a stable published contract (→ `interfaces.md`) |
| **Shared Kernel** | a small shared model two teams co-own (use sparingly — high coupling) |
| **Separate Ways** | cheaper to duplicate than integrate |

**When DDD earns its keep — and when it doesn't.** Strategic DDD pays off where the
**domain is complex and is the differentiator** (a *core* subdomain): the modelling and
ubiquitous-language discipline tame complexity that would otherwise leak everywhere. It
is **overhead, not value, for simple CRUD, generic, or supporting subdomains** — there,
buy/adopt or write it straightforwardly and spend the saved effort on the core. Applying
full DDD uniformly across every subdomain is itself an anti-pattern; the *classification*
above is what tells you where to invest.

> **Tactical DDD** (entities, value objects, repositories, factories, domain
> services) is mostly **code-altitude** — keep it out of the architecture
> description. The one tactical concept that *is* architecturally significant is the
> **aggregate**, because it defines a **consistency boundary** (what's transactional
> vs eventually consistent) — note those in the SD, not every value object.

---

## 2. Choosing the structuring pattern

Pick the *internal* shape against the drivers. The menu, with the honest trade:

| Pattern | One line | Reach for it when | Cost / avoid when |
|---|---|---|---|
| **Layered (n-tier)** | horizontal layers (UI/app/domain/data) | simple CRUD; small team; familiar | domain leaks into every layer; weak for complex domains |
| **Ports & Adapters (Hexagonal)** | domain core + pluggable adapters at the edges | testability, swappable I/O, deferring tech choices | ceremony for trivial apps |
| **Clean / Onion** | hexagonal + concentric dependency rings | rich domain, long-lived, many integrations | over-engineered for a thin service |
| **Vertical Slice** | organise by feature, not by layer | feature-churny apps; reduce cross-layer coupling | shared logic can drift; needs discipline |
| **Modular Monolith** | one deployable, hard module boundaries inside | the **default** for most new systems | a "monolith" of mud if boundaries aren't enforced |
| **Microservices** | independently deployable services per context | independent scaling/deploy/teams at real scale | distributed-systems tax; an *org* decision, not a default |
| **Event-Driven** | components react to events via a broker | temporal decoupling, fan-out, audit, ingestion | harder to reason about flow; eventual consistency |
| **Pipeline / Dataflow** | stages transforming a stream | batch/stream processing, ETL, compilers | poor fit for interactive request/response |

**Defaults and reversibility (the architect's bias):**
- **Modular monolith first.** It gives you clean boundaries (so you *can* split
  later) without the operational tax. Splitting to microservices is then a localized
  decision per context, not a big bang. Reach for microservices when an *independent*
  scaling, deployment, or team-autonomy driver demands it — not by fashion.
- A structuring choice is a **one-way-ish door** (`methods.md` §1) — costly to undo.
  That's exactly what an ADR is for. The *boundaries* matter more than the *style*:
  good boundaries make the style swappable; bad ones don't.

**The principles underneath** (Robert C. Martin's *component* principles — these are
the architecture-altitude cousins of SOLID, and more relevant here than SOLID itself):
- **Cohesion** — what goes *in* a component: **REP** (release together), **CCP**
  (things that change together — closure), **CRP** (things used together).
- **Coupling** — how components relate: **ADP** (no cycles), **SDP** (depend in the
  direction of stability), **SAP** (stable = abstract). The **Dependency Rule**
  (Clean Architecture) is SDP applied: source-code dependencies point *inward*, toward
  the domain; this is **DIP scaled up** — the one SOLID principle that is genuinely
  architectural.
- **Enforce them, don't just preach them.** A no-cycles check (`ADP`) and a
  layer/dependency rule are ideal **fitness functions** — `arch_lint.py`/ArchUnit
  rules in CI (`automation.md`, `methods.md` §11). A principle you can't test, you
  don't have.

> **SOLID itself is code-altitude.** Cite it for the implementer; don't write it into
> an architecture description. Its architectural payload is *DIP → the Dependency
> Rule* and the component principles above.

---

## 3. Selecting tactics & patterns for a quality scenario (forward catalogue)

`methods.md` §7 is the **demand** side — it turns a concern into a measured `Q.xx`
scenario. §11 is **recovery** — what tactic existing code already uses. This section
is the missing **supply** side: given a scenario, here is the menu of **tactics**
(the SEI term; Bass, Clements & Kazman, *Software Architecture in Practice*, 4th ed.,
SEI Series) and patterns you design *with*. The cloud/distributed entries are grounded
in the **Microsoft Azure Architecture Center** ("Cloud Design Patterns") and
**microservices.io** (Chris Richardson); the messaging entries in **Enterprise
Integration Patterns** (Hohpe & Woolf). **Each selection is an ADR** whose driver is the
`Q.xx` it serves — and **every tactic buys one quality at the cost of another**
(a circuit breaker buys fault tolerance at the cost of complexity and fail-fast
rejections; caching buys performance at the cost of staleness). Record the quality you
*gave up*, not only the one you bought (ATAM trade-off point, `methods.md` §11).

**Tactic → ISO/IEC 25010:2023 characteristic** (names per `standards.md`):

| Quality (25010) | Tactics / patterns to reach for |
|---|---|
| **Reliability** (availability, fault tolerance, recoverability) | redundancy & replication · health check · **circuit breaker** · **bulkhead** · timeout · retry + backoff + jitter · **idempotency** · graceful degradation · failover |
| **Performance efficiency** (time, resource, capacity) | caching · read replicas / **CQRS** read models · async + queue · load balancing · connection pooling · data locality · **backpressure** |
| **Flexibility** (scalability *(25010:2023)*, adaptability) | stateless services · sharding / partitioning · horizontal scale-out · event-driven decoupling · feature flags |
| **Security** (overlaps the mandatory threat model) | gateway / BFF · authn/z at the edge · secrets management · encryption in transit & at rest · rate limiting · input validation (→ HLD §8, `privacy.md`) |
| **Maintainability** (modularity, modifiability, testability) | ports & adapters · ACL · layering · the component principles (§2) · contract tests (`interfaces.md`) |
| **Compatibility** (interoperability) | published language / OHS · API gateway · message translator (EIP) · versioned contracts (`interfaces.md`) |

**Integration style** — choose *per boundary*, then record it; the style is itself an
architectural commitment (`significance.md` item 6):

| Style | Use when |
|---|---|
| **Synchronous request/response** (REST/gRPC) | the caller needs the answer now; simple causality |
| **Asynchronous events** (pub/sub, broker) | temporal decoupling, fan-out, buffering, audit trail |
| **Batch / file transfer** | high volume, latency-tolerant, legacy interop |

For *how* messages move once you go async — channels, routers, translators,
aggregators, request-reply vs pub-sub — use **Enterprise Integration Patterns**
(Hohpe & Woolf; already the solution-altitude reference in `standards.md`). Reuse the
styles the landscape already uses unless there's a reason not to (`methods.md` §4).

**Data & consistency patterns** (these *follow from* your bounded contexts, §1):
- **Saga** (orchestration vs choreography) — a business transaction across contexts
  without a distributed lock; pick orchestration for visibility, choreography for
  decoupling.
- **Outbox** — atomically persist state *and* the event to publish (no dual-write).
- **Event Sourcing** — state as an event log; powerful but a one-way door — adopt
  only for a real audit/temporal driver, never by default.
- **CQRS** — split read and write models; pairs with event sourcing and read replicas.
- **Eventual consistency** — the default *between* contexts; strong consistency stays
  *inside* an aggregate (§1).

**Evolution / migration patterns** (Strangler Fig, ACL, branch-by-abstraction,
parallel run) live in `migration.md` — reach for them whenever the work transforms an
existing system rather than greenfield.

---

## 4. Agile / evolutionary architecture — the stance (not the ceremonies)

Scrum roles, sprints and standups are **SDLC process, out of scope** for an
architecture skill. But *how much* architecture to do up front, and *when*, is an
architectural stance this skill already embodies — worth naming so it's deliberate:

- **Just-enough / emergent architecture.** Decide what's costly to reverse now; defer
  the rest. This *is* the Triage table and `significance.md`.
- **Last Responsible Moment.** Make a one-way-door decision at the latest point you
  still have the information to make it well — not earlier (premature lock-in), not
  later (you've already coded around the gap). This is `methods.md` §1's reversibility
  test in time.
- **Architecture runway / enablers.** Build just enough structural capacity ahead of
  the features that need it; capture a significant enabler as an **RFC → ADR**
  (`governance.md`), explore an unknown with a **spike**.
- **Evolutionary architecture / fitness functions** (Ford, Parsons & Kua). The
  architecture is allowed to change *because* its essential qualities are guarded by
  automated checks (`methods.md` §11, `automation.md`). This is what makes "defer the
  decision" safe rather than reckless.

For the **delivery** sense of *vertical slicing* — splitting a story so each increment
cuts through all layers and delivers value — see `business-analysis.md` §3
("Splitting"). That is the *process* twin of the *architectural* Vertical Slice style
in §2; keep the two senses distinct.

---

## 5. What stays a pointer (and why)

Be economical (the skill's own rule). These are real and useful, but they live at the
code or process altitude — **cite them, link out, don't expand them into the
architecture description:**

- **GoF design patterns** (Strategy, Factory, Observer, …) — class/object-level
  vocabulary for the implementer.
- **Patterns of Enterprise Application Architecture** (Fowler, PoEAA) — Repository,
  Unit of Work, Data Mapper, Active Record are tactical/code. The *style-level* ones
  do surface here: **Transaction Script vs Domain Model** is a §2 structuring choice,
  and **Service Layer** is a common pattern. **CQRS** (Greg Young) is detailed in §3.
- **SOLID** — code-altitude; its architectural payload is in §2 (DIP → Dependency
  Rule + component principles).
- **Data-oriented design** (SoA, cache locality, ECS) — an implementation/performance
  technique owned by the `game-engine-guru` skill; here it is at most a *performance
  tactic* behind a `Q.xx` scenario, or a recognised *style* (`methods.md` §9).
- **Scrum / Kanban / SAFe ceremonies** — team process; only the *architecture stance*
  (§4) is in scope.

---

## 6. Standards & sources (grounding)

This file is **not** invented guidance — each claim traces to a standards body or its
originating author. Consolidated so it's auditable (full mapping in `standards.md`):

| Topic (this file) | Grounded in | Body / author |
|---|---|---|
| Decision = ADR; views | **ISO/IEC/IEEE 42010:2022** | ISO/IEC/IEEE |
| Tactic → quality names | **ISO/IEC 25010:2023** (SQuaRE) | ISO/IEC |
| Strategic DDD, subdomains, context mapping (§1) | **O-AA Standard** ("DDD strategic patterns"); *Domain-Driven Design* (Evans, 2003); *Implementing DDD* (Vernon) | **The Open Group**; Evans; Vernon |
| Architectural tactics & quality scenarios (§3) | *Software Architecture in Practice*, 4th ed. (**SEI** Series); ATAM | **SEI / CMU**; Bass, Clements, Kazman |
| Component cohesion/coupling principles, Dependency Rule (§2) | *Clean Architecture*; *Agile Software Development* (REP/CCP/CRP, ADP/SDP/SAP) | Robert C. Martin |
| Hexagonal / Ports & Adapters (§2) | "Hexagonal Architecture" | Alistair Cockburn |
| Cloud/distributed patterns — circuit breaker, bulkhead, retry, CQRS, event sourcing, strangler (§§2–3) | **Cloud Design Patterns**, Azure Well-Architected Framework | **Microsoft Azure Architecture Center** |
| Saga (orchestration/choreography), transactional outbox, microservice decomposition (§3) | **microservices.io** pattern language; *Microservices Patterns* | Chris Richardson |
| Messaging / integration patterns (§3) | *Enterprise Integration Patterns* | Hohpe & Woolf |
| Evolutionary architecture, fitness functions (§4) | *Building Evolutionary Architectures* | **Thoughtworks** — Ford, Parsons & Kua |
| Architecture runway, intentional vs emergent (§4) | **SAFe** (Architectural Runway); Continuous Architecture | **Scaled Agile, Inc.**; Erder, Pureur & Woods |
| Strangler Fig (§3), Anti-Corruption Layer (§§1, 3) | martinfowler.com; *DDD* (Evans) | Fowler; Evans (see `migration.md`) |

When a claim and a team's mandated standard disagree, **conform to the team's** (the
skill's standing rule, `standards.md`); record the divergence in an ADR.

## When to use what — the one-screen version

1. **New system or unclear boundaries?** → §1. Find subdomains, classify core/
   supporting/generic, draw bounded contexts on the language/change/data/consistency
   seams. *Then* pick a structure.
2. **Picking the internal shape?** → §2. Default to a **modular monolith** with
   enforced boundaries; go distributed only on a real independence driver. Enforce
   the component principles with a CI fitness function.
3. **A `Q.xx` scenario to meet?** → §3. Pick the tactic that serves *that* quality;
   record the trade-off (it always costs another quality) as an ADR.
4. **Crossing a boundary?** → §3 integration style + EIP; name the context-mapping
   relationship (§1).
5. **Transforming an existing system?** → `migration.md`.
6. **Every one of the above** → derive from a driver, weigh ≥ 2 options, **write the
   ADR** (`methods.md` §8, `significance.md`).

Cross-references: boundaries & decisions — `methods.md` §§1, 4, 8; significance —
`significance.md`; quality scenarios — `methods.md` §7, `standards.md`; contracts —
`interfaces.md`; transformation — `migration.md`; enforcement — `automation.md`.
