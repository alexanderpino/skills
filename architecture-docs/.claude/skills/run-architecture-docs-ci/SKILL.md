---
name: run-architecture-docs-ci
description: >-
  Run, test, and smoke-check the architecture-docs CI tooling — the
  Architecture-as-Code validator (arch_lint.py) and house-style detector
  (detect_doc_conventions.py) shipped under assets/ci/. Use to validate a
  docs/architecture tree, lint ISO/IEC/IEEE 42010 conformance, check ADR/RFC
  front-matter, run the gate locally, or prove the linter still catches
  violations. No app/GUI — these are Python CLIs.
---

# run-architecture-docs-ci

The `architecture-docs` skill ships a CI bundle at `assets/ci/` — two
**pure-stdlib Python 3 CLIs** (no app, no GUI, no server):

- `assets/ci/tools/arch_lint.py` — the **gate**: validates a `docs/architecture`
  tree (front-matter, ISO/IEC/IEEE 42010 conformance, ARCH-REF drift, links).
  Exit `1` on any error (or any warning under `--strict`), else `0`.
- `assets/ci/tools/detect_doc_conventions.py` — learns an org's house style into
  `house-profile.yaml`, which `arch_lint.py --house` then enforces.

The agent path is the smoke driver `driver.sh`. It does **not** lint this repo —
it builds throwaway fixture docs trees in a temp dir and asserts the validator
(1) **passes** a conformant tree, (2) **fails** a deliberately broken one and
catches each seeded violation, and (3) round-trips the house-style detector.
A linter that never fails is worthless, so the driver verifies both directions.

> Paths below are relative to `architecture-docs/` (the unit root). The driver
> lives at `.claude/skills/run-architecture-docs-ci/driver.sh`.

## Prerequisites

Python 3.8+ only — no `pip install`, no third-party deps. Verified on 3.11.15.
PyYAML is used if present and silently falls back to a built-in parser if not.

```bash
python3 --version          # 3.8+; tested on 3.11.15
```

## Run (agent path) — the smoke driver

From the unit root (`architecture-docs/`):

```bash
bash .claude/skills/run-architecture-docs-ci/driver.sh
```

Prints a per-assertion `PASS`/`FAIL` log and ends with `DRIVER OK` (exit 0) or
`DRIVER FAILED` (exit 1). Last verified run: **8 passed, 0 failed**. What it
asserts, in order:

1. `arch_lint all` exits **0** on a conformant 42010 fixture tree.
2. `detect_doc_conventions` writes a non-empty `house-profile.yaml`.
3. `arch_lint all --house <profile>` still exits **0** (house rules don't break a clean tree).
4. After seeding four faults, `arch_lint all` exits **1** and the output contains:
   `unknown viewpoint VP-GONE`, `invalid status 'review'`,
   `superseded ADR must set 'superseded-by'`, and `still has ❌`.
5. The committed worked example under `examples/brownfield-api-keys/` (a full doc set
   authored from a *given* epic + functional requirements + story acceptance criteria for an
   existing service) still lints clean — guarding the skill's authoring workflow against
   regressions.

No screenshots — these are CLIs; the PASS/FAIL log is the observable output.

## Run the tools directly (against a real docs tree)

Point `--root` at a target repo's `docs/architecture`. These exact invocations
were run this session (against fixture trees) and exit 0 on a clean tree:

```bash
# the full gate (what CI runs)
python3 assets/ci/tools/arch_lint.py all --root docs/architecture --src src

# individual checks
python3 assets/ci/tools/arch_lint.py frontmatter --root docs/architecture
python3 assets/ci/tools/arch_lint.py conformance --root docs/architecture

# learn the house style, then enforce it
python3 assets/ci/tools/detect_doc_conventions.py --root docs/architecture --out docs/architecture/house-profile.yaml
python3 assets/ci/tools/arch_lint.py all --root docs/architecture --src src --house docs/architecture/house-profile.yaml
```

Syntax sanity (the tools are stdlib-only, so compiling is a full smoke check):

```bash
python3 -m py_compile assets/ci/tools/arch_lint.py assets/ci/tools/detect_doc_conventions.py
```

## Run (human / CI path)

The same `arch_lint.py all` runs as a GitHub Action — see
`assets/ci/workflows/architecture-as-code.yml`. Output uses
`::error::`/`::warning::` annotations so failures surface inline on the PR.
That workflow is the deployed form of the `arch_lint all` command above; the
driver is the local equivalent and needs no network or tokens.

## Gotchas

- **The driver lints fixtures, not this repo.** This repo has no
  `docs/architecture` tree — the skill *templates* live in `assets/templates/`
  and are full of `<placeholders>`. Running `arch_lint` against
  `assets/templates/` is **not** a valid smoke test (no `AD.md` root, every
  placeholder warns). Always test against a real or fixture docs root, which is
  exactly what `driver.sh` constructs.
- **`review` vs `in-review`.** The validator only accepts `in-review`; `review`
  is an error. The RFC template uses `in-review`. The driver seeds `review` on
  purpose to confirm the check fires.
- **`conformance-checklist.md` warns "missing 'level'".** It carries no
  `level:` field by design, so a harmless `WARN` appears on every run. Warnings
  don't fail the gate (exit stays 0) unless you pass `--strict`.
- **Unfilled `<placeholder>` front-matter** is a `WARN` normally but an `ERROR`
  under `--strict` — useful to catch templates committed without being filled in.
- **`--src` is required for the drift check.** Without it, ARCH-REF drift is
  skipped (an `info:` line), not failed.

## Troubleshooting

- `::error:: docs root not found: docs/architecture` → wrong `--root`; pass the
  actual docs directory. `arch_lint.py` exits `2` here (usage), distinct from
  `1` (lint failure).
- `house profile found but PyYAML not installed; skipping house enforcement`
  (an `info:` line) → house rules are skipped without PyYAML; install it
  (`pip install pyyaml`) only if you need `--house` enforcement. Core checks
  still run.
- Driver prints `DRIVER FAILED` → a check regressed; the per-assertion log names
  which one. Re-read the failing `grep` in `driver.sh` against the tool's output.
