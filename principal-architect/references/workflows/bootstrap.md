# Workflow: bootstrap

Give a repository its first architecture docs, or recover the as-is architecture of an
existing codebase, for the slice the work actually touches. The result is the minimal
conformant set (index, AD root, checklist, decision log), the documents the slice
needs, and the first decision records. All of it then goes through the normal change
lifecycle.

**Slice boundary.** Document the slice named, not the whole repository (SKILL.md
Triage, rule 2). Scaffolding happens only after the user confirms the plan; nothing
outside the docs root changes unless they asked for the CI bundle.

`ARCH` below means `python3 <skill-dir>/scripts/arch.py`, where `<skill-dir>` is the
directory holding this skill's SKILL.md. Run it from the repository root and always
pass `--json`. The CLI is the source of truth for state; never infer what it reports.

**Input**: the slice to document (a component, a flow, the area a coming change
touches), and optionally whether to install the CI gate.

## Steps

1. **Check whether there is anything to bootstrap**

   ```bash
   ARCH context --json
   ```
   - `state: "ok"` → the docs exist; this is not a bootstrap. Route the work to the
     consult or propose workflow and stop.
   - `state: "no_docs_root"` → continue. Note `root` and `root_resolved_by`.

2. **Settle the location and the house style**

   - If `root_resolved_by` is `default`, check `README`, `CONTRIBUTING`, `mkdocs.yml`
     or a docusaurus config for a pointer to where docs belong. If one exists, rerun
     with `--root <that path>` (or add `root:` to `.architecture.yml`).
   - Look for existing documentation of any kind (ADRs in another folder, wiki
     exports, `*.feature` files, issue templates). If there is some, learn its
     conventions first:
     ```bash
     python3 <skill-dir>/assets/ci/tools/detect_doc_conventions.py --root <that folder> --out <root>/house-profile.yaml
     ```
     and write everything after this step in that shape (`references/house-style.md`).

3. **Plan the scaffold**

   ```bash
   ARCH init --json                 # add --with-ci to install the validator and CI workflow
   ```
   Show the `plan` (every file marked `create` or `keep`) and ask the user to confirm.
   Offer `--with-ci` when the repository has CI and no architecture gate.

4. **Scaffold, on the user's yes**

   ```bash
   ARCH init --yes [--with-ci] --json
   ```
   The files are templates. Leave them as they are for now: filling them for the
   slice is part of the change's tasks (step 6), so it is planned, reviewed and
   verified like everything else.

5. **Recover the slice**

   Reverse-engineer what is there before designing anything: the archaeology method in
   `references/methods.md` §3 for an ordinary codebase, or the pipeline in
   `references/reverse-engineering.md` for a large or polyglot one. Mark what you
   recovered as recovered (`source: recovered` on documents, `derivation: recovered`
   on ADRs that record decisions already in the code).

6. **Run the slice through the change lifecycle**

   ```bash
   ARCH new bootstrap-<slice> --title "Document <slice>" --archetype greenfield --json
   ```
   Then continue at step 6 of the propose workflow (`references/workflows/propose.md`):
   fill `change.md` from what step 5 found, mint the first ADR(s), write the tasks
   (the index and AD root filled for the slice with rows that do not apply deleted,
   HLD context and container views, the SD for the slice, the PRD driver stub for what
   exists, the checklist). Stop when status is `ready`, as propose does; apply,
   verify and archive follow on the user's request.

## Output

```
## Bootstrapped: <root>

**Scaffolded:** <files created> · **CI gate:** <installed | not installed>
**House style:** <detected from <folder> | none found; skill defaults>
**Slice:** <slice> — planned as change `bootstrap-<slice>` (<state>)

Next: review the plan, then `/arch-apply bootstrap-<slice>`.
```

## Guardrails

- Never scaffold before the user confirms the plan.
- Never retro-document the whole codebase; one slice per bootstrap.
- Recovered is not designed: mark which is which.
- Never invent stakeholders, drivers or numbers to make the AD root look complete;
  record them as gaps.
