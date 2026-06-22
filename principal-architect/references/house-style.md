# House style — detect & conform to the organisation's conventions

Every organisation documents differently — its own **mandatory sections**, front-matter
fields, ID schemes, terminology, tone, and per-type formats (ADR style, user-story syntax,
acceptance-criteria style). This skill's templates are **defaults, not law**: when a house
convention exists, it **overrides** the default. So the first move on any existing project is
to *learn the house style and conform to it*, for **every** document type — not just user
stories. Only when no convention exists do you fall back to the skill's defaults and, after
confirming, create a reusable house template.

This generalises the user-story format-learning in `business-analysis.md` §2 to all documents.

## What counts as "house style"

- **Mandatory / standard sections** — headings the org expects in a given doc type (e.g. a
  required *Data Privacy Impact*, *Regulatory*, *Rollback*, or *Sign-off* section in every HLD).
- **Front-matter fields** — required metadata (owner, domain, classification, jira-key,
  cost-centre, review flags) and their allowed values.
- **ID & naming schemes** — `ADR-NNNN` vs `PROJ-123`; file naming; folder layout.
- **Per-type formats** — ADR (Nygård vs MADR vs Y-statements), user story (Connextra vs
  custom), acceptance criteria (Gherkin vs checklist), diagram conventions.
- **Terminology & tone** — the ubiquitous language, capitalisation, and voice the org uses.

## Detect it (tooling + signals)

Run the bundled detector, which clusters docs by type and infers each type's required
front-matter, **mandatory sections**, ID scheme, and format signals:

```bash
python tools/detect_doc_conventions.py --root docs/architecture \
  --out docs/architecture/house-profile.yaml \
  --emit-templates docs/architecture/_house     # optional: starter house templates
```

It writes a machine-readable **`house-profile.yaml`** (conventions per type) and can emit a
starter template per type built from the detected mandatory sections + required fields. Also
look manually for: `.github/ISSUE_TEMPLATE/`, `.gitlab/issue_templates/`, `**/*.feature`
(Gherkin), existing templates/`CONTRIBUTING`/style guides, and the patterns in existing docs.

Example `house-profile.yaml` (excerpt — note the company-specific HLD section):

```yaml
types:
  HLD:
    required_frontmatter: [id, title, status, owner, domain, classification]
    mandatory_sections: [Overview, System context, Containers, Data Privacy Impact,
                         Security — threat model, FinOps — cost estimate]
  ADR:
    mandatory_sections: [Status, Context, Decision, Consequences]   # detected: Nygård
    formats: { adr_style: nygard }
  US:
    formats: { story_format: connextra, ac_style: gherkin }
    mandatory_sections: [Story, Acceptance criteria]
```

## Conform, and enforce

1. **Conform.** Produce every new/updated doc in the detected house format — match its
   sections, field names, ID scheme, and tone. House sections are **added to**, never
   substituted for, the skill's safety-critical ones (a house style can *add* a mandatory
   section but should not drop the threat model or FinOps estimate; if it conflicts, raise it).
2. **Record.** Commit `house-profile.yaml` at the docs root. The skill reads it on later runs
   so conventions are reused, not re-derived.
3. **Enforce in CI.** `arch_lint.py` auto-loads `house-profile.yaml` (or `--house PATH`) and
   fails the build when a doc of a given type is missing a house-required field or mandatory
   section. House conventions thus become gated, not merely suggested (`automation.md`).
4. **Create when absent.** If no house style exists, use the skill defaults, confirm with the
   owner, and save the chosen shape as the house template + a first `house-profile.yaml`.

> Principle: the skill *adapts to the company*, it does not impose one house style on every
> company — while never dropping the safety-critical content (ISO 42010 required content,
> threat model, FinOps) that conformance depends on.
