# Business analysis — user stories & acceptance criteria

The agent is also a **master business analyst**: it elicits needs, decomposes them into
well-formed user stories with testable acceptance criteria, and traces them to the
architecture. Crucially, **every organisation writes these differently** — so the first job
is to *detect and conform to the company's house format*, learning from existing examples,
and only generating a template when none exists. Grounding: **IIBA BABOK® Guide v3** and its
**Agile Extension** (the BA standard); INVEST (Bill Wake); the Connextra story format; Gherkin
(BDD). This complements ISO/IEC/IEEE 29148 and the PRD's functional drivers.

## 1. Where BA sits in the hierarchy (traceability)

```
Business capability (EA §4)
  └─ Epic        (EP-NNN — large outcome, weeks–months)
      └─ Feature     (≈ a PRD functional driver F.xx — a coherent slice of value)
          └─ User story  (US-NNN, fits one iteration)  ──▶ Acceptance criteria  ──▶ Tests
```

Each artifact carries a stable ID (`references/conventions.md` §1): an **epic** is `EP-NNN`,
a feature maps to a functional driver `F.xx`, a story is `US-NNN`. Every story links **up**
to its epic (`epic: EP-NNN`) and the functional driver it serves (`satisfies: [F.xx]`), and
ultimately an EA capability; and **down** to the tests that confirm its acceptance criteria.
That chain (`capability → EP-NNN → F.xx → US-NNN → AC → test`) is the BA contribution to
end-to-end traceability. Capture each epic in the lean `epic.md` template (`EP-NNN`: outcome,
parent capability, child `F.xx`/stories, epic-level acceptance) so the parent of a story is a
real, greppable record — not just a free-text label.

## 0. Working from requirements you're already given

For **existing software** the inputs usually already exist — a backlog of epics, a list of
functional requirements, user stories with acceptance criteria. **Ingest them; do not
re-elicit what you've been handed.** Map each one onto the skill's structure, preserving the
original wording and (where possible) the original IDs:

| You're given | Maps to | Action |
|---|---|---|
| An **epic** / large outcome | `EP-NNN` (`epic.md`) | One epic record; link it up to a capability, down to its `F.xx`/stories. Keep the house ID if it has one. |
| A **functional requirement** / feature | `F.xx` in the **PRD** §4 | One functional driver; phrase with RFC 2119 keywords; note the source. |
| A **user story** | `US-NNN` (`user-story.md`) | One story, in the **house format** (detect it first, §2); set `epic:` and `satisfies:`. |
| **Acceptance criteria** | the story's *Acceptance criteria* section | Copy them verbatim into the story; only reshape if they're not testable (§4). |
| A **non-functional / quality** expectation | `Q.xx` (PRD §5, 6-part scenario) | Don't bury it in a story — promote it to a quality driver and reference `Q.xx`. |

The architecture work (HLD/SD/AD, recovered ADRs) is then **reverse-engineered from the
existing code** (`references/reverse-engineering.md`, `methods.md` §3) and traced back to these
ingested drivers. Fill only the genuine gaps, and record anything the given inputs leave
unanswered as a *visible* assumption — never invent a driver to look complete.

## 2. Detect & conform to the company's format — do this FIRST

Do **not** impose a house style. Derive it from evidence, exactly like the architect's
evidence discipline (`methods.md` §10). User-story/acceptance-criteria format is one instance
of the general **house-style** discipline that applies to *every* document type — see
`references/house-style.md` and the `detect_doc_conventions.py` tool, which can infer the
story format (Connextra/Gherkin) and mandatory sections automatically.

1. **Find existing examples.** Search the repo and trackers for how the org already writes
   stories and acceptance criteria:
   - `**/*.feature` files → Gherkin/BDD is in use (Given/When/Then).
   - `.github/ISSUE_TEMPLATE/`, `.gitlab/issue_templates/`, `.azuredevops/` → issue/story
     templates with the mandated fields.
   - Existing PRDs, backlog exports, or docs containing "As a … I want … so that …",
     "Acceptance criteria", "Definition of Done", story-point/T-shirt sizes.
   - Tracker conventions (Jira/Azure DevOps/Linear): story ID scheme, custom fields,
     labels, the "definition of ready/done".
2. **Infer the house template.** Extract the *actual* convention: the story syntax and role
   taxonomy, the acceptance-criteria style (Gherkin vs rule list), the ID scheme, the
   estimation unit, required fields (priority, component, DoD), and tone/formatting.
3. **Conform.** Write every new story/criterion in *that* format. Match their field names,
   ordering, and wording style. Consistency with the house style beats any "better" template.
4. **Only if none exists** → propose the well-grounded default below, confirm it with the
   user, then **create a reusable house template** in the repo (`user-story-template.md`) so everything
   after is consistent. Record the chosen convention in `conventions.md`/the repo so future
   work reuses it rather than re-deciding.

> The point: the skill *learns* the organisation's format and becomes consistent with it —
> it does not flatten every company into one house style.

## 3. Writing the user story (default format, if you must create one)

**Connextra format:** `As a <role>, I want <goal/action>, so that <benefit/why>.`
Keep the *role* specific (not "user"), the *goal* solution-free, and the *benefit* real.

**INVEST** — a good story is **I**ndependent, **N**egotiable, **V**aluable, **E**stimable,
**S**mall, **T**estable. If a story fails one, reshape or split it.

**3 C's** (Ron Jeffries): the story is a **Card** (placeholder), a **Conversation** (the real
detail), and a **Confirmation** (the acceptance criteria). The card is not the whole spec.

**Splitting** big stories (keep each valuable and testable): by workflow step, by business
rule/variation, by data type/parameter, by happy-path vs edge-case, by operation (CRUD), or
spike-out-the-unknown. Never split into technical layers (UI/API/DB) — that breaks "Valuable".

## 4. Writing acceptance criteria

Acceptance criteria define the **minimum conditions for the story to be accepted** and must be
**verifiable as true/false** (BABOK 10.1). Two common styles — use whichever the house uses:

**a) Gherkin / Given–When–Then (scenario-based, BDD):**
```gherkin
Scenario: <name>
  Given <initial context>
  And   <more context>
  When  <action/event>
  Then  <observable outcome>
  And   <another outcome>
```
Good when behaviour is conditional or example-driven; maps directly to automated tests
(Cucumber/SpecFlow/Behave). Cover the happy path **and** the key edge/negative cases.

**b) Rule-oriented checklist:**
```
- [ ] <a single, testable condition that must hold>
- [ ] <another condition, including an error/edge case>
```
Good for simple, enumerable conditions. Each item is independently verifiable.

Each criterion: testable, unambiguous, no implementation detail, and tied to the story's
benefit. Non-functional expectations (performance, security) reference the PRD quality drivers
(`Q.xx`) rather than being re-specified per story.

## 5. Definition of Ready / Done

- **Definition of Ready (DoR):** the story is clear, estimable, has acceptance criteria, and
  dependencies are known — i.e. it's safe to start. (Conform to the house DoR if one exists.)
- **Definition of Done (DoD):** the shared checklist for "complete" (tests pass, AC met,
  docs/ADR updated, reviewed, deployed). Detect and reuse the org's DoD; don't invent a rival.

## 6. Quality bar & anti-patterns

A master BA refuses to ship:
- Stories that are really tasks ("Add an index to the users table") — no user value → it's a
  task, not a story.
- Acceptance criteria that aren't testable ("works well", "is fast" — quantify or point to a
  `Q.xx`).
- Solutioning inside the story (prescribing the *how*) — that belongs in the SD/ADR.
- Stories with no role or no benefit ("so that …" missing) — the *why* drives prioritisation.
- A different format from the rest of the backlog — inconsistency is itself a defect here.
