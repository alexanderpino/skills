# Architecture-as-Code — CI bundle

Ready-to-run validation for the architecture documentation. The core validator
(`arch_lint.py`) is **pure Python standard library** — no install needed; it uses PyYAML
if present, otherwise a built-in front-matter parser.

## Files (copy into your repo)

| In this bundle | Copy to | Purpose |
|---|---|---|
| `tools/arch_lint.py` | `tools/arch_lint.py` | the validator (gate) |
| `tools/detect_doc_conventions.py` | `tools/detect_doc_conventions.py` | learn the org's house style → `house-profile.yaml` |
| `spectral.yaml` | `.spectral.yaml` | optional Spectral ruleset for front-matter |
| `workflows/architecture-as-code.yml` | `.github/workflows/architecture-as-code.yml` | CI workflow |

## House style (any document type)

Companies have their own conventions — mandatory sections, front-matter fields, ID schemes,
ADR/story formats. Learn them once, then enforce them:

```bash
# Detect conventions for EVERY doc type and write a machine-readable profile
python tools/detect_doc_conventions.py --root docs/architecture \
  --out docs/architecture/house-profile.yaml \
  --emit-templates docs/architecture/_house     # optional starter templates

# arch_lint auto-loads house-profile.yaml and fails when a doc of a given type is
# missing a house-required field or mandatory section (e.g. a mandated "Data Privacy
# Impact" section in every HLD). Or point at it explicitly:
python tools/arch_lint.py all --root docs/architecture --src src --house docs/architecture/house-profile.yaml
```

House conventions **override** the skill's default templates (while never dropping the
safety-critical ISO 42010 / threat-model / FinOps content). See `references/house-style.md`.

## What `arch_lint.py` checks

- **frontmatter** — required fields, allowed `status`/`level` values, `ADR-NNNN`/`RFC-NNNN`
  id format, reciprocal supersession links, and the **mandatory Threat-model + FinOps**
  sections (and review flags) in every `HLD`/`SAD`.
- **conformance** — ISO/IEC/IEEE 42010: every concern framed by a known viewpoint, every
  view governed by exactly one known viewpoint, ≥1 stakeholder/concern/viewpoint/view, ≥1
  ADR, and no unresolved ❌ in `conformance-checklist.md`.
- **drift** — every `ARCH-REF: ADR-NNNN` in `--src` points to an existing, non-superseded
  ADR; flags accepted ADRs that no code references.
- **links** — relative Markdown links inside the docs root resolve.

## Local usage

```bash
# Run the full gate (exit non-zero on any error)
python tools/arch_lint.py all --root docs/architecture --src src

# Individual checks
python tools/arch_lint.py frontmatter --root docs/architecture
python tools/arch_lint.py conformance --root docs/architecture
python tools/arch_lint.py drift       --root docs/architecture --src src

# Treat warnings (e.g. unfilled <placeholders>) as errors
python tools/arch_lint.py all --root docs/architecture --strict

# Emit a YAML bundle for Spectral
python tools/arch_lint.py all --root docs/architecture --emit-frontmatter build/frontmatter.yaml
npx @stoplight/spectral-cli lint build/frontmatter.yaml --ruleset .spectral.yaml
```

Output uses GitHub Actions annotations (`::error::`, `::warning::`) so failures surface
inline on the pull request. Exit code: `1` if any error (or any warning under `--strict`).

## Pre-commit (optional)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: arch-lint
        name: architecture docs lint
        entry: python tools/arch_lint.py all --root docs/architecture --src src
        language: system
        pass_filenames: false
```

## Notes

- The optional CI jobs (Spectral, markdownlint, Structurizr render, Infracost) are
  `continue-on-error` / conditionally run so the **gate** never depends on external tooling
  or network. Promote them to required checks once you've wired in the tokens you want
  (e.g. `INFRACOST_API_KEY`).
- `arch_lint.py` targets Python 3.8+.
