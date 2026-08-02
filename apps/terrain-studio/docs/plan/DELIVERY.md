# Terrain Studio — delivery policy

This document controls **how** the canonical Sprint 1–10 stories are delivered. The sprint files,
ADRs, and `GROUNDING.md` continue to control **what** is built and the behavior it must prove.

The optimization is boundary placement, not reduced quality: focused evidence runs on each changed
slice; exhaustive evidence runs once on the integrated wave. The same unchanged artifact is never
rebuilt, recaptured, or re-reviewed merely because it crossed another process state.

## Measured problem

On 2026-08-02 the canonical mission had 26 open items, one building item, one verifying item, and
26 leases held across two items. S1.3–S1.5 were already product-green at 79/79 with zero skips, but
publication remained blocked by runner behavior. Mission metrics showed completed merges taking
seconds while repeated build/verification and retry states took minutes to hours.

The delivery bottleneck is therefore duplicated certification and shared-file serialization, not
missing product implementation.

## Operating rules

1. **Start from the accepted story.** Existing sprint contracts, ADRs, and grounded claims are not
   researched or plan-reviewed again. Open research only for a named unresolved claim that changes
   implementation; it blocks that story, not the whole programme.
2. **Deliver vertical slices.** One coherent story slice includes production behavior, persistence
   and UI integration where applicable, its focused oracle, and migration. R0–R5 are concerns to
   satisfy inside the slice, not six phase boundaries or six commits.
3. **Use the lightest safe execution path.** Mission Control is reserved for concurrent work with
   real lease contention, shared contracts, high-risk migrations, or merge coordination. A local,
   disjoint change owned by one implementer uses an ordinary branch/worktree and the gates below.
4. **Keep at most four implementation lanes.** A lane starts only with disjoint semantic ownership
   and an executable focused gate. Unrelated lanes continue when one lane is blocked.
5. **Integrate continuously.** Merge a focused-green slice promptly. Do not wait at research,
   review, sprint, or wave boundaries when the next dependency is ready.
6. **Cache artifacts, never verdicts.** Built bundles, captures, and oracle outputs may be reused
   only when their content key matches source tree, lockfile, Node major, Vite version, build mode,
   and test inputs. Missing or mismatched evidence is red.
7. **No silent rebaselines.** Baseline generation is a separate explicit command. Verification
   only compares against reviewed immutable expectations.

## Change classes and gates

Classify by the highest-risk surface touched. A higher class includes the lower-class checks that
apply to its changed behavior.

| Class | Typical change | Required before merge |
|---|---|---|
| **L — local** | isolated plugin, inspector control, copy/layout, local pure helper | focused oracle with non-zero assertions; existing armed negative control referenced or a new control observed red; relevant static check |
| **N — numerical** | evaluator, terrain formula, lattice, seed, mask, physical field | L + direct digest with `skipped = 0`; square/hex and unit/boundary cases required by the story; visual evidence once for changed visible terrain |
| **C — contract** | ports, schema, persistence, migration, cache identity, graph runtime | N where numerical + migration round-trip/idempotence + plugin/bridge checks + independent review |
| **R — runtime** | GPU, renderer, PWA, export, worker/process runner | applicable C checks + production build + focused built-bundle oracle + ownership/cleanup/budget evidence named by the story + independent review |

An existing oracle's negative control is armed **once** when the oracle is introduced or changed.
Later stories reference that recorded red endpoint and run the oracle green; they do not repeatedly
mutate unchanged production or regenerate the same evidence.

## Integration-wave gate

Run this once after a group of focused-green commits is integrated, before those stories are marked
`DONE`:

1. relevant static checks (`plugins:check`, `bridge:check`) once;
2. one production build from the integrated source;
3. built-bundle digest with all registered types and `skipped = 0`;
4. all standalone oracles through the isolated runner, with non-zero selected and assertion counts;
5. PWA/e2e only when shell, service worker, browser workflow, renderer interaction, or export flow
   changed;
6. visual spot-check of each changed visible feature; expand to its full matrix only on drift or
   when the story introduces a new visual contract.

The full sweep is mandatory at this boundary and at final release. It is not repeated for every
story, reviewer, merge preparation, and publication step. A failed wave gate reruns the failed
oracle and its affected dependency family during repair, then reruns the complete wave gate once.

## Review policy

- Independent review is mandatory for C/R changes, security-sensitive behavior, data loss risk,
  physical-model changes, and any change whose focused evidence was ambiguous.
- L/N changes receive one integration review at the wave barrier. Separate plan, code, merge, and
  post-merge reviewers are not required for the same unchanged diff.
- Review findings are repaired in the same slice and the focused gate is rerun before scope widens.
- Accepted ADRs are reopened only when the implementation needs a different decision. No new ADR is
  created merely to authorize an already-specified story.

## Work removed from the critical path

- no fresh Scout and Plan Reviewer cycle for an already grounded, accepted story;
- no programme-wide block because an unrelated sprint claim remains unresolved;
- no full standalone sweep or production rebuild at every story phase;
- no repeated visual capture matrix for unchanged terrain;
- no separate commit for baseline, contract, gate arming, implementation, integration, and close;
- no replay of byte-identical product evidence without a source/toolchain/input hash change;
- no Mission Control lifecycle for a routine one-owner change with no semantic contention;
- no roadmap, ADR, or grounding expansion while implementation-ready work exists, except to resolve
  a concrete blocker in that work.

## Delivery waves

Waves are dependency barriers, not timeboxes. Pull the next ready item immediately when a lane frees.

### Wave 0 — recover delivery and finish Sprint 1

- Finish MC-S33 only to its reviewed runner contract; do not widen it into a general CI platform.
- Publish the runner, then replay MC-S04 product commits by content identity in one retry item.
- Reuse unchanged visual/product evidence by hash; rerun focused source/built gates, digest, and the
  integration-wave gate on the published runner.
- Mark S1.3–S1.5 `DONE` only after the integrated wave is green.

### Wave 1 — publish the keystone and independent foundations

Primary lane: S2 typed ports/evaluation (`MC-S01` then `MC-S02`). In parallel, use disjoint lanes
for S9 domain/dialog/import provenance (`MC-S21`) and S10 capability probing (`MC-S25`). These are
already specified and do not wait for unrelated grounding closure.

### Wave 2 — fan out after typed ports

Run the first actually independent bundles in parallel:

- cover/state foundation (`MC-S05`);
- Gerstner renderer foundation (`MC-S09`);
- graph machinery (`MC-S18`);
- large-world evaluator/regions (`MC-S22`).

Extract field/context, evaluator/document, and renderer/water boundaries only when the next two
ready bundles demonstrably contend on the same file. Each extraction must be digest-preserving and
land before the dependent features; scaffolding is not a separate architecture programme.

### Wave 3 — physical stack

Pull S3 completion, then physical hydrology, while graph machinery, water rendering, and large-world
work continue on disjoint ownership. Climate starts as soon as its actual S3/S4 dependencies close.
Do not serialize the independent renderer path behind physical-water work.

### Wave 4 — export, regimes, and large-world integration

Complete export after S2–S5; run geology/regime stories as their specific dependencies close; join
S8 and S9 manifest/preset work without waiting for unrelated stories in either sprint.

### Wave 5 — Extreme Detail

S10.R0 calibration remains the only global readiness exception because its bounds do not yet exist.
Run that calibration while earlier waves execute. Start each S10 implementation bundle as soon as
its own dependencies and measured bounds are satisfied. This wave now includes exact arbitrary
dimensions, GPU-only paged evaluation of the complete production node registry, and Walkaround/
reachability. Boundary Landforms may land earlier after typed descriptors; its 16K GPU gate closes
here. Walkaround uses bounded Rapier collision pages while generation remains GPU-only.

## Visible delivery checklist

This checklist is mirrored in `PROGRESS.md` and updated whenever state changes.

- [ ] MC-S33 runner focused suite and full sweep classified green
- [ ] MC-S33 reviewed, integrated, and published
- [ ] S1.3–S1.5 replayed on the published runner and Sprint 1 closed
- [ ] S2 typed-port keystone published
- [ ] First four disjoint Wave 2 lanes started
- [ ] S3–S5 physical stack integrated
- [ ] S6/S8/S9 integration complete
- [ ] S10.R0 calibrated and S10 delivered
- [ ] 16K and arbitrary-dimension GPU-only graph gates green
- [ ] Boundary Landforms and no-flight Walkaround/reachability delivered
- [ ] Final built digest, standalone sweep, e2e/PWA where applicable, and audit green

## Delivery metrics

Record only metrics that can change a decision:

- focused-green cycle time per slice;
- integration-wave cycle time and failed oracle family;
- active implementation lanes versus lease-blocked lanes;
- cache hit/miss with validated content key;
- delivered stories and points per wave.

If process or infrastructure consumes a second cycle while product evidence remains green, isolate
that defect and continue every unaffected lane. Do not hold the whole programme behind one runner,
review, documentation, or shared-file issue again.