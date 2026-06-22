# Methods — how a master architect derives the content

Templates tell you *what* a document contains. This file tells you *how to arrive at
the content* and how to reason about it like a principal architect, so the docs
reflect the real system and the real decisions — not guesses dressed up as facts.

**Contents**
1. Mindset — operate as a master architect
2. Pick the altitude — enterprise, solution, or software
3. Deriving the architecture from an existing codebase (archaeology)
4. Enterprise & solution discovery (capabilities, landscape, options)
5. Identifying stakeholders & concerns
6. Eliciting drivers (business · functional · quality)
7. Deriving quality attribute scenarios (ISO 25010 + quantification)
8. Recovering and making decisions
9. Recognising patterns, styles & smells
10. Evidence discipline — derive, then ask, then assume (visibly)
11. Evaluating an existing architecture (ATAM-lite)

---

## 1. Mindset — operate as a master architect

You are not filling templates; you are reconstructing and stewarding the intent of a
system. Carry these stances into every step:

- **Start from drivers, not code.** Ask "what must this system be *good at*, and for
  whom, and why?" Structure follows from quality attributes and constraints, not the
  other way around.
- **Make trade-offs explicit.** Every significant choice trades one quality for
  another. Name the tension, the sensitivity points, and what you gave up — not just
  what you gained (ATAM thinking).
- **Judge reversibility.** A one-way door (expensive to undo: a public interface, a
  data model, a dependency with lock-in) deserves an ADR and care. A two-way door
  (cheap to reverse) deserves speed, not ceremony.
- **Recover the *why*, not just the *what*.** Code shows what is; your job is to
  reconstruct why it is that way, and to record it before it's lost.
- **Protect conceptual integrity.** Prefer choices consistent with the system's
  existing style over locally-optimal novelties. Flag drift.
- **Be economical.** The best documentation is the *least* that preserves the
  decisions and structure worth preserving. Volume is a cost, not a virtue.
- **Be honest about uncertainty.** Derived a fact? Show the evidence. Couldn't?
  Mark it an assumption or a known gap. Never fabricate stakeholders, drivers, or
  numbers.

---

## 2. Pick the altitude — enterprise, solution, or software

Before anything else, decide which level the work lives at — it sets the entity of
interest, the frameworks, and the artifacts (full table in `standards.md`). Signals:

- **Enterprise** — the work concerns the *organisation's* capabilities, the whole IT
  landscape, a portfolio standard, a principle, a roadmap, or cross-programme
  governance. Words like "capability", "landscape", "standardise across teams",
  "target operating model". → TOGAF/ArchiMate, `enterprise-architecture.md`.
- **Solution** — the work delivers *one solution to a business problem that spans
  several systems or integrations*, or chooses major technologies / build-vs-buy.
  Words like "integrate A with B", "end-to-end", "which platform", "the X solution".
  → `SAD.md`.
- **Software** — the work is *inside one system/application*: components, modules,
  patterns, interfaces, a refactor, a feature. → C4 + `AD/PRD/HLD/SD`.

Most coding tasks are **software** level — don't drag TOGAF into a refactor. But a
single request can touch two levels (e.g. a new integration is a *solution* decision
that lands as *software* changes in two systems); produce artifacts at each level it
genuinely touches, and link them (`complies-with:` up, `realizes-capabilities:` down).

## 3. Deriving the architecture from an existing codebase (archaeology)

When docs don't exist yet, reconstruct the architecture from evidence before writing
a line. Work outside-in: boundary → containers → components → flows.

**Entry points & containers** — what runs?
- Build/manifest files: `CMakeLists.txt`, `package.json`, `Cargo.toml`, `go.mod`,
  `pom.xml`, `pyproject.toml`, `Dockerfile`, `*.csproj`. They name targets, binaries,
  services, and the tech stack.
- `main`/entrypoints: `grep -rn "int main\|func main\|if __name__\|fastapi\|http.ListenAndServe"`.
- Top-level directories and ownership: `ls`, `CODEOWNERS`, `MAINTAINERS`.

**Boundaries & dependencies** — what talks to what?
- Internal structure: namespaces/modules/packages, include/import graph
  (`#include "..."`, `import`, `use`, `require`). Dense clusters = components.
- External systems: outbound calls, SDK/client usage, env vars and config keys
  (`grep -rn "http\|grpc\|connect(\|getenv\|os.environ\|process.env"`), and the
  service list in compose/k8s manifests.
- Data stores: DB clients, ORM models, migrations, file I/O, queue clients, schema
  files.

**Runtime** — how does a key job flow?
- Pick one important use case from the request or README and trace it from entry
  point through the call graph to its outputs. That trace becomes a runtime view.

**Tech & process** — CI config, test layout, release scripts reveal build/test/deploy
shape and quality expectations.

Synthesise into: a container view (the runnable parts), a component view per
interesting container, one or two runtime traces, and a context view (users +
external systems). Name elements with the terms the code already uses, and record
those terms in the glossary.

## 4. Enterprise & solution discovery (capabilities, landscape, options)

At higher altitudes the evidence is different — derive accordingly.

**Business capabilities (enterprise)** — what the organisation *can do*, independent
of how. Derive from: the product/portfolio docs, org structure, the value streams the
request implies, existing system responsibilities (a system usually realizes one or
more capabilities). Build a capability map; mark maturity and which apps support each.
Capabilities are stable; org charts and apps churn beneath them.

**Application & technology landscape (enterprise)** — inventory the systems and their
relations: each app, the capability it serves, the data it owns, its status
(keep/retire/replace), and the integrations between them. Sources: a service catalog,
repos/manifests across the estate, network/integration config, deployment inventories.
Express baseline → target → **gap**; the gaps drive the roadmap.

**Solution option analysis (solution)** — the solution architect's core craft:
1. State the problem, the in-scope systems, and the enterprise principles/capabilities
   it must honour.
2. Generate **2–4 genuine end-to-end options** — build, buy, extend, and the
   integration style for each (sync API vs async events vs batch). Include the boring
   standard option.
3. Score each against the cross-cutting NFRs (ISO 25010) and the principles; surface
   the integration and data-ownership consequences.
4. **Build-vs-buy**: weigh total cost, fit, lock-in, control, and time-to-value — not
   just licence price. Record as an ADR (`level: solution`).
5. Choose technologies with rationale (this is where vendor/product selection legitimately
   happens, unlike enterprise Phase D).

**Integration archaeology (solution)** — to map how existing systems already talk:
trace contracts at the boundaries (API specs, message schemas, shared DBs, file drops),
note sync vs async, and the error/idempotency behaviour. Reuse beats reinvention —
prefer the integration styles the landscape already uses unless there's a reason not to.

**Migration / modernization (solution/enterprise)** — when the work is a *transformation*
of an existing system (local-to-global, on-prem→cloud, monolith→distributed/SaaS): pick a
**7 R's** strategy per workload, recover the **As-Is from runtime** (distributed
tracing/APM/logs → traced sequence diagrams), choose transition patterns (Strangler Fig,
ACL, event-driven intermediary), and document the staged path with rollback per interim
state. Full method, pattern selection, data/protocol mapping and grounding are in
`references/migration.md`; the artifact is `transition-architecture.md`.

---

## 5. Identifying stakeholders & concerns

**Stakeholders** — derive, don't invent:
- Who *builds* it: contributors, `CODEOWNERS`, team docs.
- Who *operates* it: deployment targets, runbooks, on-call docs, infra config.
- Who *uses/integrates* it: the public API/CLI surface, SDK consumers, README
  "getting started", example clients.
- Who is *affected*: end users, downstream systems, compliance/security owners.
- The **request context** itself names stakeholders ("so external engineers can…").

If a role is plausible but unconfirmed, list it and mark it inferred — then ask.

**Concerns** — each stakeholder has interests; turn them into concerns:
- A concern is a need/goal/risk/quality, phrased so a view can address it
  ("How do I integrate without source?", "Will it hold p99 under load?").
- Every concern must (a) trace to ≥ 1 stakeholder, (b) be framed by ≥ 1 viewpoint,
  and (c) often map to an ISO 25010 quality characteristic. That triple is the
  conformance backbone (AD.md §3/§5).

---

## 6. Eliciting drivers (business · functional · quality)

**Business drivers (`B.xx`)** — the "why it exists / why now":
- Sources: product README, project charter, the motivation in the request, the
  commercial or research context. These are often *not* in the code.
- Master move: if the business rationale isn't evidenced, **ask one crisp question**
  rather than inventing it; record what you're told. Don't manufacture business goals.

**Functional drivers (`F.xx`)** — the "what it must do":
- Sources: the request/spec, the existing feature set, the API surface, and
  **the tests** — tests are executable specifications of intended behaviour.
- Phrase with RFC 2119 keywords so obligation is exact; give each a means of
  verification (often "a test exists / will exist").
- **Decompose into user stories + acceptance criteria** (`US-NNN`) for delivery — and
  **detect and conform to the organisation's house format first** (Gherkin, a Jira/issue
  template, a role taxonomy, a DoD); only create a template if none exists. Method:
  `references/business-analysis.md`.

**Quality drivers (`Q.xx`)** — the "how well": see §5; this is where architects earn
their keep, because quality attributes shape structure.

---

## 7. Deriving quality attribute scenarios (ISO 25010 + quantification)

This is the highest-leverage derivation. Three steps:

**a) Map concern → ISO 25010:2023 characteristic.** Translate each quality concern to
one of the nine characteristics (functional suitability, performance efficiency,
compatibility, interaction capability, reliability, security, maintainability,
flexibility, safety) and a sub-characteristic. This gives a shared, standard name.
(Full catalogue in `standards.md`.)

**b) Quantify from evidence — find the real numbers before asking.** Architects hunt
for existing measures:
- Performance: benchmark results, timeouts/retries, resource limits, batch sizes,
  frame budgets, SLA/SLO docs, rate limits, k8s requests/limits.
- Reliability: error budgets, retry/backoff config, health checks, replica counts.
- Security: authn/z config, threat-model docs, compliance requirements.
- Maintainability/flexibility: module count, change frequency (git log), coupling.
The Cambridge method's baselines ("t1 seconds", "overhead ≤ 10%") come from exactly
this kind of evidence. Use the measured baseline as the scenario's starting point.

**c) Write the 6-part scenario** (source · stimulus · environment · artifact ·
response · **response measure**) and a **means of verification**. If, and only if, no
number can be derived, state the scenario and mark the measure `TBD — needs target`
and ask the owner. A quality requirement without a measure is a wish; flag it as such
rather than pretending.

**Prioritise with a quality/utility tree** (ATAM): characteristic → refinement →
scenario, each rated for business value and architectural difficulty. The high-value
/ high-difficulty scenarios are where design effort and ADRs concentrate.

---

## 8. Recovering and making decisions

**Recovering a past decision ("why is it like this?") — retroactive ADR.** When the
code embodies a significant choice with no record:
- Reconstruct the **context** from evidence: `git log`/`git blame` on the relevant
  files, PR/issue discussions, code comments, and the shape of the code itself
  (what alternative it clearly avoids).
- Write the ADR with `status: accepted`, dated to when you *recovered* it, and mark
  any inferred rationale explicitly ("inferred from commit history / code shape").
  Recovering the decision now stops it being re-litigated later.

**Making a new decision — forward ADR.** Reason it through, don't just pick:
1. Frame the problem and the **decision drivers** (which `B/F/Q` are in tension).
2. Generate **2–4 genuine options** — including the boring/standard one.
3. Evaluate each against the drivers; surface sensitivity points (where a quality
   hinges on this choice) and trade-off points (where qualities conflict).
4. Decide, in active voice, and record the **consequences** honestly — the costs and
   new risks, not only the benefits.
5. Add the `ARCH-REF:` marker at the code site that enacts it.
Use Nygård by default; reach for the MADR option fields when the options genuinely
need a pros/cons comparison (`references/standards.md`).

---

## 9. Recognising patterns, styles & smells

- **Styles/patterns**: infer from structure — layering, pipeline/dataflow, facade,
  event-driven, ECS, modular monolith, microservices. Name the style in the HLD
  "solution strategy"; if you're *adopting* one, that's an ADR.
- **Smells → anti-patterns** (record in "Known issues / debt", tag the quality they
  threaten): god object / mega-service (maintainability, performance), cyclic
  dependency (maintainability), dense undecomposed structure (modifiability),
  deficient/near-duplicate names (communication). Detect via the dependency graph and
  simple metrics (file/dir size, fan-in/out, cycle detection). Recording a smell is a
  legitimate outcome — a deliberate "we accept this for now" beats silent debt.

---

## 10. Evidence discipline — derive, then ask, then assume (visibly)

The order matters, and it's what separates an architect from a guesser:

1. **Derive from evidence first.** Code, configs, tests, manifests, git history,
   existing docs. Most of §§2–7 is derivable.
2. **Ask the human only for what can't be derived and matters** — typically business
   drivers, relative priorities, and target SLAs/quality thresholds. Ask few, precise
   questions; batch them; don't block trivial work on them.
3. **Record what you couldn't settle as a visible assumption or gap** — an ADR with
   `status: proposed`, a measure marked `TBD`, or a "Known inconsistencies" entry in
   AD.md §7. Visible uncertainty is correctable; invented certainty is a landmine.

Never fabricate a stakeholder, a driver, or a number to make a template look complete.
A conformant-but-false document is worse than an honest, partial one.

---

## 11. Evaluating an existing architecture (ATAM-lite)

Documenting a system tells you *what it is*; **evaluating** it tells you *whether it's any
good for what it must do*. This is a distinct, high-value output for **existing software** —
before a migration, an acquisition/due-diligence, or a "should we keep investing in this?"
call. It is **not** the ISO conformance checklist (that audits whether the *docs* are
complete); it judges the *architecture*. Artifact: `architecture-evaluation.md`.

Use a lightweight **ATAM** (SEI; Bass, Clements & Kazman). The steps that matter:

1. **Set the yardstick.** Reuse the prioritised quality-attribute scenarios (`Q.xx` utility
   tree, §7). You can't evaluate "good" without naming the qualities that matter and their
   measures. If they don't exist, derive them first (§7).
2. **Recover the approaches.** For each scenario, find the tactic the architecture actually
   uses (caching, replication, a queue, layering) — from the design and code (§3, §9).
3. **Probe for the four findings:**
   - **Risk** — a decision/gap that threatens a quality goal.
   - **Non-risk** — a decision confirmed sound (record it; it's evidence, not filler).
   - **Sensitivity point** — a measure that hinges critically on one element.
   - **Trade-off point** — one decision that helps quality A and hurts quality B (the
     highest-value findings; this is where ADRs concentrate).
4. **Cluster risks into themes** — themes drive the roadmap, not individual risks.
5. **Recommend** — each significant risk becomes a proposed **ADR** or a debt entry; the set
   feeds a `transition-architecture.md` if the system is headed for change.
6. **Make it continuous.** Turn the top scenarios into **fitness functions** (evolutionary
   architecture — Ford, Parsons & Kua): automated checks (a cycle test for maintainability, a
   latency-budget test for performance, an `arch_lint`/ArchUnit rule) so the qualities are
   verified every build, not assessed once. A fitness function is the executable form of a
   `Q.xx` scenario's *means of verification*.

Keep it proportional: a one-page evaluation of the three scenarios that matter beats a
40-page report nobody reads. Grounding and the wider scenario-based family (SAAM, CBAM for the
cost dimension) are in `references/standards.md`.
