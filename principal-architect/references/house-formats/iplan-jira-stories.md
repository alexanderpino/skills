# Known house format — I-Plan (RGN IT), Jira stories

Pre-detected house format for user stories/subtasks across **all I-Plan repos**
(`services-*`, `core`, `libraries`, `database`, `clockregistrations`, etc.). The format
lives in Jira, not in repo files, so `detect_doc_conventions.py` can't discover it —
apply this directly instead of re-eliciting it per project. Confirmed against
NLRGN-716 (Talent profile), NLRGN-1265/1266 (Health/Client integration), stories
PR-26601–PR-26609, and NLRGN-1267 (contacts portal authentication), stories
PR-27052–PR-27076 — see [Precedent index](#precedent-index) for which set to fetch as a
worked example.

For the underlying wiki-markup/REST mechanics (curly braces, `{code:c#}`, custom field
discovery) see the `rgn-jira-wiki-formatting` skill — this file only covers the
I-Plan-specific *content* conventions on top of that.

## Project & linking — the critical gotcha

**`fields.project.key` is always `"PR"`**, never the epic's `NLRGN-*` prefix. Epics live
in project `NLRGN`; stories and subtasks are created in project `PR` and cross-linked to
the epic via the Epic Link field (`customfield_10006`). Getting this wrong lands the
story directly under `NLRGN` with an `NLRGN-*` key instead of a `PR-*` one — has happened
before. Re-check `fields.project.key == "PR"` on every create payload regardless of what
epic key appears elsewhere in the description.

## Title format

```text
[Component] (Size) Story Title
```

- Sizes: `XS`, `S`, `M`, `L`
- Components: see the table below. A story that genuinely spans two components uses both,
  slash-separated (`[BLO/Adapter]`) — but that is a smell outside the post-migration cleanup
  category, because it usually means two merge requests in two repos, which is a split.

## Component → role table

Use a specific, component-owning role in the User Story section — generic "I-Plan
Developer" is too vague to signal ownership.

| Component | Role | Owns |
| --- | --- | --- |
| `[Adapter]` | *As an I-Plan Adapter Developer* | `iplanadapter` (Spring Boot/Camel, Java) |
| `[BLO]` | *As an I-Plan BLO Developer* | `core` business-logic services |
| `[BFF]` | *As an I-Plan Service Developer* | `libraries` + the per-domain `services-*` BFFs |
| `[Token Handler]` | *As an I-Plan Token Handler Developer* | `token-handler` (Express/TS, BFF token-handler pattern) |
| `[SPA]` | *As an I-Plan Portal Frontend Developer* | `online-spa-widgets/rgn-frontend` (NX monorepo) |
| `[Client]` | *As an I-Plan Planner* (user-facing) | the planning client UI |
| `[Database]` | *As an I-Plan Developer* | `database` (Liquibase changesets) |
| `[Infrastructure]` | *As an I-Plan Infrastructure Engineer* | `group-infra`, per-service Terraform |
| `[Test]` | *As an I-Plan Test Engineer* | `functional-tests`, E2E coverage |
| `[Planning]` | *As an I-Plan Solution Architect* | migration sequencing, rollout, readiness |

`[BFF]`, `[Token Handler]`, `[SPA]` and `[Test]` were added from NLRGN-1267, where the SD
used them and the original six could not express the work. Note that `[SPA]` work is written
against the `rgn-frontend` NX monorepo (`apps/iplan`, `libs/iplan/*`, and the shared
`libs/token-handler`), **not** against the 16 `online-spa-widgets/ci-cd/i-plan/<module>-{rnl,ttg}`
repos — those hold only Terraform and CI that deploy published `@rgn-frontend/*` packages, so
sizing an `[SPA]` story against them will be wrong.

## Precedent index

Fetch one of these as a worked example before drafting; it is cheaper and more accurate than
re-deriving the shape from this file alone.

| Epic | Stories | Use it as the example for |
| --- | --- | --- |
| NLRGN-716 | Talent profile | The original x-one integration shape |
| NLRGN-1266 | PR-26601–PR-26609 | Client integration: the 8 reusable categories, end to end |
| NLRGN-1267 | PR-27052–PR-27076 | Authentication/authorization work: `[Token Handler]`, `[BFF]`, `[SPA]`, `[Test]` tags; conditional stories; verifying an SD's seed list |
| NLRGN-1323 | PR-26609, PR-26618, PR-26623, PR-27076 | The post-migration cleanup category, one story per domain |

## Description sections (Jira wiki markup)

```text
h2. Context

Brief background explaining why this work is needed.

h2. Objective

One-sentence goal of this story.

h2. User Story

*As a [role]*, I want to [action], *so that* [benefit/outcome].

h2. Technical Requirements

* Bullet point list
* Of technical tasks
* And implementation details

h2. Acceptance Criteria

* *Scenario: Name*
** *Given* precondition
** *When* action occurs
** *Then* expected outcome

h2. Technical Notes

Links to solution designs, related documentation, dependencies.
```

## Reusable story categories (x-one integration epics)

These recur across every entity domain (Talent, Client, Assignment, Placement, ...) —
swap `[Entity]` for the domain and adjust scope, don't reinvent the shape:

1. **[Adapter] Implement [Entity] Profile Retrieval Endpoint** — dual-source (x-one JSON
   / Mondriaan XML), feature toggles per OpCo, API endpoint with `adapterContext`.
2. **[Adapter] Implement Proxy Event Transformation & BES Subscriptions** — listen to
   MGM/NL One GEO topics, transform to generic proxy event. Adapter publishes 1:1
   immediately — **no bundling at the adapter level**.
3. **[BLO] Implement Generic BES Event Sink & Notification Queueing** — REST endpoint,
   persist to `BES_NOTIFICATION` table, check entity exists before queueing.
4. **[BLO] Adapt Sync Job for Dual-Mode Processing** — `BesNotificationsJob` handles both
   JSON and XML. Bundling happens **here** (one snapshot per entity per batch), not at
   the adapter.
5. **[Database] Store and Manage Global IDs** — schema extensions, bi-directional
   global↔local lookup, indexes.
6. **[Planning] Prepare Migration Strategy and Readiness Checks** — per-OpCo rollout
   sequence, edge-case analysis (multi-CompanyNumber, uncorrelated), rollback procedure.
7. **[Client] Enable Manual [Entity] Data Retrieval** — UI for global-ID input, pre-fill
   from retrieved data, handle multi-CompanyNumber selection (MGM legacy).
8. **[BLO/Adapter] Implement Follow-up Changes Post-Migration ([Domain])** — remove
   legacy/Mondriaan code, feature toggles, deprecated mappings.

## Epic assignment rule for post-migration cleanup

Story 8 (cleanup) **always** links to the consolidated post-migration epic (NLRGN-1323),
never the build epic (e.g. NLRGN-1265/1266) — cleanup can't complete until *all*
integrations across every domain have migrated, so it's tracked centrally. Append the
domain to the title: `[BLO/Adapter] (L) Implement Follow-up Changes Post-Migration (Client)`.

## An SD's story table is a proposal, not a backlog

RSO solution designs often end with a "JIRA Stories" table, usually labelled as a proposal to
seed story creation. **Verify every row against the code before creating anything.** On
NLRGN-1267, checking the 23 seeded rows against the repos changed 13 of them and produced 6
stories the table never mentioned:

- 2 rows **dropped**: one already built (an Adapter `/health` endpoint that existed and was
  already wired as the ECS health check), one redundant (a nightly purge job duplicating the
  session store's own TTL expiry).
- 2 rows **rescoped**, because the work already existed in a different form than the title
  implied: a `/logout` story where that endpoint already existed but front-channel, so the real
  gap was a *new* back-channel endpoint; and an SPA "link to logout" story where the shared
  front-end library already did it, leaving only verification and failure handling.
- 3 rows **collapsed into another row** — same endpoint, same behaviour, no independent
  deliverable.
- 1 row had to **split**, because its two call sites live in different repos: two merge
  requests, two contracts, so two stories.
- 5 rows were **mis-sized**, all in the same direction — an `S` that rewrites a cookie contract
  is an `L`.
- 6 stories were **missing entirely**, including the feature-toggle store that three other
  stories assumed already existed, and the BLO function replacing the system being retired.

The cheapest place to verify is the corresponding as-is documentation
(`docs/x-one/authorization-current.md` and similar), then the code it cites. Record a
`file:line` for every verdict — a verdict from the SD's own prose is not a verdict, since the
SD is what is being checked. Two failure modes to watch for specifically:

- **A row whose stated rationale is wrong even though the work is wanted.** Evaluate against the
  migration's actual goal, not the reason the SD gives; dropping the row because the reason
  does not hold loses real work.
- **A row that assumes a mechanism exists.** Grep for it. "Implement the toggle-based relay"
  presupposed a toggle store that had no schema, no code and no story.

Feed the corrections back into the SD in the same pass — the rationale fixes, the
already-built rows, and an "Open Issues & Decisions Required" section for what the analysis
could not settle. Decisions that block a story belong in the SD where the reviewers are, not in
a catch-all Jira story nobody grooms.

**But don't publish the delta itself.** The delta is a review artefact: it exists to get the
story set signed off, and once that has happened nobody needs it. Writing it into the SD as a
"seeded rows deliberately not created" table documents a decision process about a table that no
longer exists, and every future reader has to skip it.

### Replace the SD's story table with the epic, not with the story keys

The obvious move once the stories exist is to paste their keys into the SD's table. Don't — that
is a second copy of the backlog, and it goes stale the moment anyone splits, renames, retitles or
closes a story, which nobody will come back to fix. Replace the table with the epic reference and
a live query, so the page cannot drift from Jira:

```xml
<ac:structured-macro ac:name="jira"><ac:parameter ac:name="server">Jira Randstad</ac:parameter>
<ac:parameter ac:name="columns">key,summary,type,status,assignee</ac:parameter>
<ac:parameter ac:name="maximumIssues">30</ac:parameter>
<ac:parameter ac:name="jqlQuery">"Epic Link" = NLRGN-1267 ORDER BY key ASC</ac:parameter>
<ac:parameter ac:name="serverId">744c7057-a339-320f-9196-d54fe44f7436</ac:parameter></ac:structured-macro>
```

The `serverId` above is RGN's global-jira; copy it from an existing Jira macro on the same page
rather than typing it. Name any story that the query cannot reach — a cleanup story living under
NLRGN-1323 will not match an `Epic Link = <build epic>` query — as a one-line link with the
reason it sits elsewhere.

### A statement is not an open issue

When writing the open-issues section, check each item against "what would change if the answer
came back either way". If the team has already settled it and only wants the reasoning on record,
it is a **design statement** and belongs in the section it describes — not in open issues with a
decision owner attached, which asks a reviewer for a decision that has already been taken. On
NLRGN-1267 one item ("confirm the daily purge job is not needed") was really the statement *we
rely on the store's native TTL*; it moved into the session-store section, with the scenarios that
would otherwise leave a record behind, and the open-issues list got shorter.

**Re-read the remaining issues each time one is answered.** They are not independent. On
NLRGN-1267, an item recorded as "the requirement only asks for access to the legal documents, and
those are public pages, so nothing needs building" was correct until the entry design was settled
in a *different* item — at which point one population turned out to be redirected past every page
that showed those documents, making the requirement a real regression rather than a non-issue. An
answer that closes one item can promote another from cosmetic to blocking.

### An open decision still gets its story

Keeping the decision in the SD does not mean keeping the *work* out of the backlog. If an open item
would produce I-Plan work under any of its answers, create that story now — conditional, with
"establish the answer / obtain the missing input" as its **first** technical requirement and an
explicit instruction to close it as not required if the answer goes the other way. Held back, the
work exists only in an SD paragraph and in whoever remembers reading it; as a story it is visible
in the epic, it can be groomed, and it can be closed with a recorded reason.

An unknown *input* is not a reason to withhold a story — that is what its first requirement is for.
On NLRGN-1267 this was applied inconsistently at first: the introspection story sat in the epic
waiting for a revocation decision, while a legal-documents link story was held back because the
per-tenant document URLs were unknown. Same shape, opposite treatment. Check the open-issues list
against the epic and make the two agree, then point each issue's **Blocks:** line at the story it
gates.

### Recording a decision means propagating it, not deleting the issue

When an item is decided, deleting it from the open-issues list is the smallest part of the work.
Write the decision as a statement in the section it governs, dated, **with the reasoning and the
cost that was accepted** — a reader who only sees the outcome will re-open the question. Then chase
its consequences through the rest of the design and the story set, because the design was written
while the question was open and will still be hedged in several places. On NLRGN-1267, "hard cut,
every live session breaks" also had to change a security requirement that still mandated encrypted
session cookies, a STRIDE mitigation that named the cipher, a risk write-up that pointed at an
upgrade the decision had just dropped, three story bodies, and the rollout story (a hard cut is
user-visible, so it needs a release window and a briefed support desk). Grep the design for the
options that lost — the cipher name, "dual read", "drain" — rather than trusting your memory of
where they were mentioned.

Also say where a decided item went, in the open-issues preamble ("the per-OpCo toggle now sits
under *Role Resolution Logic*"). Reviewers who read an earlier version remember five numbered
items, and a list that silently drops to two reads as a page that lost content.

A story the decision kills is **not** deleted. Give it an `h2. Status` section as the first section
of the description saying it is superseded, by what, and what would revive it, and mark the local
draft's heading the same way — then leave it in the epic to be closed unbuilt. A deleted story
looks like an oversight to whoever reads the SD next; a superseded one carries its own explanation.

## Workflow

1. Fetch and review the SD from Confluence; ask clarifying questions on open TODOs.
2. If the SD carries a story table, verify it row by row per the section above and produce a
   delta table (kept / resized / rescoped / merged / split / dropped / added, one line of
   evidence each). This is the artefact to get signed off — not the stories.
3. Propose story categories from the list above, adjusted to the entity/domain.
4. Fetch a related prior epic from the precedent index to check for drift in convention.
5. Draft every story in one local file, then **create them from that file with a script** rather
   than retyping bodies into API calls — retyping long wiki-markup bodies corrupts them silently,
   and the file stays the source of truth for later edits. Keep a ledger of created keys so a
   rerun cannot double-create.
6. Create one story first as a rendering canary — pick the one with the most hostile markup
   (braces, code blocks, nested lists), not the simplest — and fetch it back with
   `?expand=renderedFields` before creating the rest (see `rgn-jira-wiki-formatting`). Re-run that
   fetch after every later re-push, listing the rendered `<h2>` headings: it costs one call and it
   catches section order that drifted out of house order during editing (`h2. User Story` comes
   before `h2. Technical Requirements`) as well as markup damage.
7. Include SD links in Technical Notes; reference prerequisite stories/epics.
8. Record the created keys back into the draft (the draft stays the source of truth for bodies),
   and in the SD replace the seed table with the epic reference plus a live JQL query — not with
   the list of keys.
