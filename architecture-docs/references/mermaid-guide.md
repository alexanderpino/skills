# Mermaid diagram guide

Embed mermaid in the doc it explains. A diagram earns its place only when it shows
something prose can't say cleanly — boundaries, a non-trivial flow, who-talks-to-
whom. If a sentence is clearer, write the sentence.

## The C4 model — mandatory levels & detail

Software architecture **must** be captured with the C4 model (Simon Brown,
https://c4model.com). The four levels zoom in progressively; which are mandatory depends
on the altitude/significance of the work:

| Level | Diagram | Shows | Detail | When **mandatory** |
|---|---|---|---|---|
| **L1 Context** | `C4Context` | the system as a box among users + external systems | lowest; no internals | **Always** for any system (HLD §2). One per system. |
| **L2 Container** | `C4Container` | deployable/runnable units (apps, services, stores) + tech | medium; no code | **Always** for any system (HLD §3). One per system. |
| **L3 Component** | `C4Component` | components inside one container + responsibilities | high; not code-level | **Required** for any container that is non-trivial or changed (SD §2). One per significant container. |
| **L4 Code** | `classDiagram`/UML | classes/types within one component | highest; implementation | **Optional** — only for a genuinely complex component; usually auto-generated from code, not hand-maintained. |

Rules: pick the **highest level that answers the question** and stop; L1+L2 are the
non-negotiable minimum for a system; L3 where a container is significant; L4 rarely and
preferably generated. For models-as-code across all levels from one source, use
**Structurizr DSL** (`diagrams/workspace.dsl`, https://docs.structurizr.com/dsl) — see the
end of this guide.

### Copy-paste snippets

**L1 — System Context:**
```mermaid
C4Context
  title L1 System Context — <System>
  Person(user, "<User>", "<what they want>")
  System(sys, "<System>", "<one-line responsibility>")
  System_Ext(ext, "<External system>", "<role>")
  Rel(user, sys, "<uses>", "<channel>")
  Rel(sys, ext, "<calls>", "<protocol>")
```

**L2 — Containers:**
```mermaid
C4Container
  title L2 Containers — <System>
  Person(user, "<User>")
  Container_Boundary(b, "<System>") {
    Container(web, "<Web app>", "<tech>", "<responsibility>")
    Container(api, "<API>", "<tech>", "<responsibility>")
    ContainerDb(db, "<Database>", "<tech>", "<what it holds>")
  }
  Rel(user, web, "uses", "HTTPS")
  Rel(web, api, "calls", "JSON/HTTPS")
  Rel(api, db, "reads/writes", "SQL")
```

**L3 — Components (inside one container):**
```mermaid
C4Component
  title L3 Components — <Container>
  Container_Boundary(api, "<API>") {
    Component(ctrl, "<Controller>", "<tech>", "<handles requests>")
    Component(svc, "<Service>", "<tech>", "<business logic>")
    Component(repo, "<Repository>", "<tech>", "<data access>")
  }
  ContainerDb(db, "<Database>", "<tech>")
  Rel(ctrl, svc, "invokes")
  Rel(svc, repo, "uses")
  Rel(repo, db, "reads/writes", "SQL")
```

**L4 — Code (only when genuinely needed; prefer generated):**
```mermaid
classDiagram
  class OrderService {
    +placeOrder(cart) Order
    -validate(cart) bool
  }
  class Order
  class OrderRepository {
    +save(order) void
  }
  OrderService --> OrderRepository : uses
  OrderService ..> Order : creates
```

## Which view answers which question

| You need to show | Use | Lives in |
|---|---|---|
| System in its environment: users + external systems | `C4Context` | HLD |
| Major deployable/runnable parts and their tech | `C4Container` | HLD |
| Internals of one container: components & responsibilities | `C4Component` | SD |
| A specific runtime collaboration over time | `sequenceDiagram` | SD (sometimes HLD) |
| A dynamic step-by-step across elements | `C4Dynamic` | SD |
| Data-type relationships (composition/association) | `classDiagram` | SD/HLD |

Pick the **highest level that answers the question** and stop. Don't draw a
component diagram when a container diagram suffices.

## C4 Context (HLD)

```mermaid
C4Context
  title System Context — Statically Guided Dynamic Binary Modification
  Person(appeng, "External application engineer", "Wants automatic parallelisation")
  System(sgdbm, "SGDBM", "Disassembles, analyses, re-assembles binaries")
  System_Ext(dynamo, "DynamoRIO", "Dynamic binary instrumentation")
  Rel(appeng, sgdbm, "Runs with a binary + analysis chain", "CLI")
  Rel(sgdbm, dynamo, "Sends basic blocks; gets re-written blocks")
```

## C4 Container (HLD)

```mermaid
C4Container
  title Containers — SGDBM
  Person(appeng, "Application engineer")
  Container_Boundary(c, "SGDBM") {
    Container(config, "Execution configuration", "bash", "Selects & orders chains")
    Container(runner, "Analysis runner", "C++", "Runs analysis blocks")
    ContainerDb(files, "Results store", "Filesystem", "Intermediate analysis results")
  }
  Rel(appeng, config, "Configures a chain")
  Rel(config, runner, "Triggers")
  Rel(runner, files, "Reads/writes results", "files")
```

## C4 Component (SD)

```mermaid
C4Component
  title Components — Parallelisation chain
  Component(cfg, "Control flow graph", "C++")
  Component(ssa, "SSA", "C++")
  Component(cdep, "Control dependence", "C++")
  Component(loops, "Loop coverage + inter-iteration", "C++")
  Component(cls, "Parallelisation classification", "C++")
  Rel(cfg, ssa, "CFG report", "file")
  Rel(ssa, cdep, "SSA report", "file")
  Rel(cdep, loops, "Control-dependency report", "file")
  Rel(loops, cls, "Loop candidates", "file")
```

## Sequence diagram (SD)

Use for a concrete interaction with ordering, requests/responses, or alternative
paths. Show only the participants that matter to the point.

```mermaid
sequenceDiagram
  actor Eng as Application engineer
  participant Cfg as Config
  participant Run as Runner
  participant FS as Results store
  Eng->>Cfg: run(binary, chain=parallelisation)
  Cfg->>Run: execute(chain)
  loop each analysis block
    Run->>FS: write(block result)
    FS-->>Run: ok
  end
  Run-->>Eng: re-assembled binary
```

## C4 Dynamic (SD) — when ordering across elements is the point

```mermaid
C4Dynamic
  title Adding a new analysis block to a chain
  Component(dev, "Researcher")
  Component(block, "New analysis block")
  Component(chain, "Chain config")
  Rel(dev, block, "1. Implements")
  Rel(dev, chain, "2. Wires into chain order")
  Rel(chain, block, "3. Invokes via file I/O")
```

## Data types (SD/HLD) — composition vs association

```mermaid
classDiagram
  class CFGReport
  class Function
  class BasicBlock
  class Instruction
  CFGReport o-- Function : associated with
  Function *-- BasicBlock : composed of
  BasicBlock *-- Instruction : composed of
```
`*--` = composition (child can't exist without parent). `o--` = association
(logical link).

## Flowchart fallback

C4 mermaid blocks may render imperfectly in some viewers. If a renderer chokes,
or for a quick boundary sketch, fall back to a labelled `flowchart` and colour by
ownership (blue = this system, yellow = required external, purple = integrating
system — the Cambridge convention):

```mermaid
flowchart LR
  subgraph SGDBM[SGDBM]
    config[Execution config]:::own --> runner[Analysis runner]:::own
    runner -- files --> store[(Results store)]:::own
  end
  appeng([Application engineer]) --> config
  runner -- basic blocks --> dynamo[DynamoRIO]:::ext
  classDef own fill:#cfe2f3,stroke:#333
  classDef ext fill:#fff2cc,stroke:#333
  classDef integ fill:#e1d5e7,stroke:#333
```

## Enterprise & solution views (ArchiMate / TOGAF in mermaid)

Mermaid has no native ArchiMate notation. Represent higher-altitude views as layered
flowcharts, colouring by ArchiMate layer (motivation/strategy/business/application/
technology) and using nesting for realization.

**Business capability map (enterprise, TOGAF Phase B):**
```mermaid
flowchart TB
  subgraph L0[Strategy]
    g[Goal: grow self-service]:::strat
  end
  subgraph L1[Capabilities]
    c1[Customer onboarding]:::cap
    c2[Billing]:::cap
    c3[Analytics]:::cap
  end
  g --> c1 & c3
  classDef strat fill:#f5e6ff,stroke:#333
  classDef cap fill:#ffe0b2,stroke:#333
```

**Layered landscape (enterprise/solution, business→application→technology):**
```mermaid
flowchart TB
  subgraph B[Business layer]
    p[Onboard customer]:::biz
  end
  subgraph A[Application layer]
    kyc[KYC service]:::app
    crm[CRM]:::app
  end
  subgraph T[Technology layer]
    node[KYC API node]:::tech
  end
  p --> kyc --> crm
  kyc -.realized by.-> node
  classDef biz fill:#fde9d9,stroke:#333
  classDef app fill:#cfe2f3,stroke:#333
  classDef tech fill:#d9ead3,stroke:#333
```

**Solution landscape (solution):** use a C4 `C4Context`/System-Landscape or a flowchart
spanning the systems involved (see the SAD template §3). Show systems as nodes,
integrations as labelled edges (contract + sync/async), and external SaaS in the
"external" colour.

Keep the ArchiMate intent even without the notation: distinguish *active structure*
(who/what acts), *behavior* (what happens), and *passive structure* (data acted on),
and use realization edges (`-.realized by.->`) to link a higher layer to the one below.

## Migration & transition views

For modernization/migration work, show the coexistence of old and new explicitly:
- **Strangler Fig / coexistence** — a router in front, legacy + new behind, an event bus and
  ACL between (full snippet in `references/migration.md` §3).
- **Transition states** — a simple left-to-right chain `Baseline → T1 → T2 → Target` makes the
  staged path legible (see the `transition-architecture.md` template).
- **As-Is sequence diagrams** — recovered from runtime (tracing/APM/logs) as a normal
  `sequenceDiagram`, tagged `source: traced` in the SD; compare against the designed (To-Be)
  one to reveal drift (`migration.md` §4).

## Rules of thumb

- One idea per diagram. If it needs a legend longer than the diagram, split it.
- Label edges with the data/contract that flows (e.g. "CFG report", "file"),
  matching the data-type names used in the SD.
- Keep diagrams in sync with the prose around them — a stale diagram misleads more
  than missing one. If you change the design, change the diagram in the same edit.

## Models-as-code: Structurizr DSL (the C4 source of truth)

For anything beyond a couple of diagrams, define **one C4 model** in Structurizr DSL and
render every level/view from it (https://docs.structurizr.com/dsl). The diagram can then
never drift from the model, and CI can export SVGs (`automation.md`).

```text
workspace {
  model {
    user = person "User"
    sys  = softwareSystem "System" {
      web = container "Web app" "tech"
      api = container "API" "tech"
      db  = container "Database" "tech"
    }
    user -> web "uses"
    web  -> api "calls"
    api  -> db  "reads/writes"
  }
  views {
    systemContext sys { include * autolayout lr }   // L1
    container sys      { include * autolayout lr }   // L2
    // component api  { include * autolayout lr }    // L3 per container
    theme default
  }
}
```

Store as `diagrams/workspace.dsl`; render with the Structurizr CLI in CI. Embedded mermaid
snippets (above) remain the lightweight default for a single doc.
