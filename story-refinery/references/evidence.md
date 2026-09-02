# Evidence: multi-repo code investigation

Refinement without evidence is rewording. This reference covers how to find the
change surface across several repositories cheaply and honestly.

## Contents

1. Source hierarchy
2. What a manifest contains
3. Targeted scanning
4. Contract detection and cross-repo edges
5. Convention extraction
6. Blast radius
7. Honesty rules

---

## 1. Source hierarchy

Three sources, checked per repo, first hit wins. This is the hybrid model: reuse
what another tool already knows, cache what you learn, and only scan for the
specific thing this story needs.

| Priority | Source | Cost | Staleness risk |
|---|---|---|---|
| 1 | `provided_index` - output of another skill or tool | free | high |
| 2 | `cached_manifest` - `.refinery/manifests/<repo>@<sha>.json` | cheap | none (sha-keyed) |
| 3 | `targeted_scan` - budgeted ripgrep for this story | moderate | none |

### provided_index

Any external index. Configure with a path and an adapter name:

```yaml
evidence:
  sources:
    - type: provided_index
      path: .cartographer/index.json
      adapter: code-cartographer
```

`evidence.py` reads the index generically: it looks for a list of repos with a
`name`, an optional `rev`/`sha`/`commit`, and a list of files or modules. If the
shape does not match, it logs and falls through to the next source rather than
crashing.

**Staleness handling.** Compare the index's recorded revision to
`git rev-parse HEAD`. If they differ:
- Emit a WARNING, not an error.
- Downgrade every claim sourced from that index to `[?]`.
- Re-verify any `path:line` you intend to cite with a direct read. Line numbers
  from a stale index are the single most common source of wrong citations.

### cached_manifest

Built by `evidence.py manifest`. Keyed by `<repo>@<sha>` so it is never stale by
construction - a new sha means a new manifest. `ttl_days` is enforced as well: a
manifest older than that is rebuilt regardless of sha, which is the only guard
for a directory that is not a git checkout (`<repo>@nogit`).

### targeted_scan

Hypothesis-driven. Write down what you expect to find *before* searching, then
search for it. Budgeted by `budget_files` and `budget_seconds`.

Query design that works:
- domain nouns from the story ("invoice", "entitlement", "checkout")
- the existing wrong behaviour's error string
- the interface name the story implies (`*Repository`, `*Handler`, `*Service`)
- config keys and feature flag names
- the test files first - `tests/` tells you the intended contract faster than
  `src/` tells you the actual one

Query design that wastes budget: single common words, language keywords,
anything you could get from the manifest's module map.

---

## 2. What a manifest contains

Per repo, built once per sha:

```json
{
  "name": "api",
  "root": "../api",
  "sha": "9f2c1ab",
  "generated_at": "2026-09-02T10:00:00Z",
  "languages": {"python": 412, "sql": 18},
  "commands": {"test": "pytest -q", "build": "make build", "lint": "ruff check ."},
  "entrypoints": ["src/api/main.py"],
  "modules": [{"path": "src/api/billing", "files": 22}],
  "contracts": [{"path": "openapi.yaml", "kind": "openapi"}],
  "owners": [{"glob": "src/api/billing/**", "owner": "@team-billing"}],
  "deps": {"internal": ["shared-types"], "external": ["fastapi"]}
}
```

`commands` is the highest-value field for agent briefs - it is where `done_when`
comes from. Detect it from, in order: `Makefile` targets, `package.json` scripts,
`pyproject.toml` / `tox.ini`, CI workflow files. CI workflow files are the most
truthful source, because they are what actually gates merges `[F]`.

`owners` comes from `CODEOWNERS`. It determines whether a subtask crosses a team
boundary, which is the main reason enterprise subtasks stall.

---

## 3. Cross-repo edges

Multi-repo work fails at the seams, not inside the repos. Build the edge list
explicitly.

An edge exists between repo A and repo B when any of these hold:
- B's dependency manifest names a package A publishes (`deps.internal`)
- A and B both reference the same contract file or its generated artefacts
- A's CI publishes an artefact B's CI consumes
- A shared database schema or migration directory is touched by both

For each edge, record direction: `producer -> consumer`. This is what orders the
subtasks in Phase 5.

`evidence.py contracts` infers edges from shared contract filenames and internal
package dependencies. **The dependency-derived direction is reliable; the
shared-filename direction is a guess** and the tool marks it as such. Confirm
which repo owns the file - usually the one that generates it, serves it, or has
it under version control rather than vendored - before you order subtasks on it.
Getting the direction backwards produces a plan that ships the consumer first.

The rule `[F]`:

> **A contract change ships before the code that depends on it, behind a
> compatibility window.** Producer subtask first, additive; consumer subtask
> second; removal of the old shape third, in a later story if the window spans
> deploys.

If a story requires a breaking change with no compatibility window, that is a
risk entry with an explicit deployment-ordering note, not a detail to leave to
the implementer.

### Contract globs

Defaults, extend per house:

```
**/openapi*.y*ml   **/swagger*.json   **/*.proto   **/*.graphql   **/*.graphqls
**/schema.sql      **/migrations/**   **/*.avsc    **/*.thrift
**/types/**/*.d.ts  (when published as a package)
```

---

## 4. Convention extraction

The most useful thing you can give an agent implementor is proof of how this
codebase does things - not your general knowledge of how it is usually done.

For each convention, capture the rule and one real citation:

```json
{"rule": "Handlers return Result[T, ApiError]; they never raise.",
 "evidence": "api/src/api/billing/handlers.py:44"}
```

Look for conventions in: error handling, logging, dependency injection/wiring,
test structure and naming, database access, validation placement, feature flag
usage, module boundaries.

Sample at least two files before asserting a convention. One occurrence is a
coincidence `[L]`.

---

## 5. Blast radius

Change impact analysis `[P: Bohner & Arnold, 1996]`, applied lightly:

1. **Primary set** - files that must change to satisfy the AC.
2. **Secondary set** - files that reference the primary set's changed symbols
   (callers, tests, mocks, fixtures, docs).
3. **Tertiary set** - contract consumers in other repos.

Record counts in the bundle:

```json
"blast_radius": {"repos": 2, "files_primary": 6, "files_secondary": 14, "contracts": 1}
```

Thresholds that should trigger a "split this story" recommendation `[L]`:
- more than 3 repos
- more than ~25 primary+secondary files
- more than 1 breaking contract change
- more than 2 team owners from CODEOWNERS

Report the recommendation; do not unilaterally split someone's story.

---

## 6. When the seam is not in the code yet

`contracts` finds the seams that already exist - the OpenAPI file, the proto, the
migration. It cannot find the seam a story is about to create, and on a change
that spans services that is the expensive one to get wrong.

When the boundary is genuinely unclear, run a short event storm before writing
subtasks `[P: Brandolini, EventStorming]`. The cheap version, alone or with one
other person, is enough here:

1. Write the **domain events** the story causes, past tense, in time order:
   *VAT number submitted, VAT number verified, tax calculated, order priced,
   order confirmed*.
2. For each, name **who or what triggers it** and **what data it carries**.
3. Draw the line where the *carrier* changes - where an event has to cross a
   process, a team or a deployment boundary. That crossing is the contract, and
   it is what `evidence.contracts` should record and what orders the subtasks.

The output is not a diagram to keep. It is two or three named events, each mapped
to a repo and a file, added to the change surface with the same citation
discipline as everything else. If a step in the sequence has no code behind it,
you have found either the new component or a missing question - both worth more
than the diagram.

Do not run this on a single-repo story. It costs an hour and tells you what you
already knew.

## 7. Honesty rules

- A `path:line` you did not read is a fabrication. Read before citing.
- Line numbers drift. Cite a symbol name alongside the line so the anchor
  survives: `handlers.py:44 (handle_invoice)`.
- If a repo in the config is not present on disk, say so and mark everything
  about it `ASSUMPTION`. Do not reason about repos you cannot see.
- If the budget ran out before you found the answer, say the budget ran out.
  "I could not locate the tax rounding logic within the scan budget" is a useful
  finding. A confident guess is not.
