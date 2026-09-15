# Gaia — state of the corpus

> **This file is not part of the skill.** It carries no instructions, no doctrine and nothing to
> apply. Nothing in it is loaded as guidance, no script reads it, and `check.py` cannot see it —
> `documents()` globs `references/*.md` only. It exists so that someone deciding whether to trust a
> given page can find out what has actually been checked. If you are here for the skill, read
> `SKILL.md`.

Last updated at commit `560b241`. Regenerate the numbers with the commands at the bottom rather
than trusting this paragraph; they were true when written and this file has no guard.

---

## What Gaia is

A citation-grounded reference corpus on terrain and water, for people building a game engine or an
authoring tool in the class of Gaea or World Machine. 37 documents on four axes — Generation,
Simulation, Rendering, Architecture — plus six bibliographies, three registers of what was measured
and what went wrong, and a guard script.

Its distinguishing claim is not coverage. It is that **every recommendation names a source, every
source carries a provenance tier, and the corpus records where it has been wrong.** That is also
the claim this file exists to qualify.

## The one thing to understand before using it

**Attribution is not verification, and the corpus says so in `SKILL.md`.** `check.py` proves that a
claim points at a real bibliography entry with a locator. It does not prove the cited work says
what the document claims. A green run means the citation is well-formed. Nothing more.

Where a human or an adversarial reviewer *has* read the source, the audit table below says so. That
covers 16 of 37 documents.

## Status

| | |
|---|---|
| Documents | **40** written, 13 planned, 6 explicitly out of scope (53 topics in scope) |
| Bibliography | 228 entries, 228 cited, 1 background |
| Adversarially audited | **40 of 40** |
| Corrections | **233** rows in `registers/corrections.tsv`; every one of the 40 documents carries at least one. ⚠️ **34 are `verifier=pending`** — named individually below, not counted away |
| `verified:` stamps | **4 of 40**, signed 2026-09-14. ⚠️ Each covers `## Use this` and the failure table only — 8%, 11%, 15% and 19% of its document's body. Read it as "the recommendation and the diagnoses were read", never as "the document was read" |
| Guards | `check.py` exit 0 · `--selftest` green · `index --check` current · `requote --selftest` green · CI `bites` **36 red + 5 green**, every mutation biting for the reason its row names |
| Measurement rigs | **35** in `rigs/`, 17 with saved output. Every register reference to one resolves; before 2026-09-14 they lived in a scratch directory and none did |
| Phase 0 | **closed** 2026-09-07 — the guard layer, verified by mutation under `bash -e` |

Reported metrics, none of them enforced:

| Metric | Value | What it means |
|---|---|---|
| `approximation` | **39/40** | documents stating *both* how good a recommendation is and what it costs. ⚠️ The fortieth, `shader-craft.md`, is a *tested* refusal, not a gap. ⚠️ And the metric does not require the two halves to describe the same technique: 5 documents put them over 50 body lines apart, 2 over 100 |
| `locators` | 188/267 (70%) | citations naming a section, equation or page rather than a topic |
| `propagation` | **18/287** | citations naming a section at *both* ends, so the two can be cross-checked at all |
| `reach` | 14/213 | body sections sharing no word with `## Use this` or the failure table |
| `unread` | 31/287 | citations that *declare* the source was never opened here |
| `crossrefs` | **2/381** | shared magnitudes that DISAGREE. Both are known false positives; its reach is 12% of linked pairs |

## Audit state, per document

Three tiers. Nothing here is "verified" in the strong sense — **no document carries the `verified:`
header**, which is the only one of the three channels that means a human read the cited work.

⚠️ **The tiering below predates the 2026-09-05 audit and its sittings.** Since then every document
has been through an implementer and an independent verifier, and 143 corrections carry both
signatures. That raises the middle channel a long way and moves the third not at all: an agent can
re-derive a number, run a block and read both ends of a cross-reference, and none of that is a
human having opened the paper. Read the tiers below as *what had been examined by hand before the
audit*, and `registers/corrections.tsv` as what has been examined since.

**Subject critic + adversarial verifier, findings applied** — a domain specialist audited the
document, ran its pseudocode and re-derived its numbers; a second agent then tried to *disprove*
every finding; only survivors were applied, with every HIGH re-derived by the lead.

`driver-fields` · `flow-routing` · `hydraulic-erosion` · `mask-operators` · `river-networks` ·
`stream-power` · `surface-and-scale-space` · `terrain-analysis-masks` ·
`thermal-and-aeolian-erosion` · `wave-models`

**Also had a shipping-architect pass + verifier** — reviewed a second time for whether the advice
survives a real frame budget, a real console and an artist at a slider. This found defects the
subject critics had missed, including a correctness bug.

`driver-fields` · `volumetric-clouds` · `wave-models`

**Earlier round, less durably recorded** — audited before the current process, without the
verifier layer. Treat as reviewed but not to the standard above.

`atmosphere-and-aerial-perspective` · `impact-craters` · `seamless-and-periodic` ·
`sky-and-weather-state` · `stratigraphy-and-lithology`

**Never examined — 21 documents.** No critic, no architect, no verifier. They are not known to be
wrong; they are unexamined, which is a different thing.

`caustics` · `coastal-erosion` · `gpu-driven-culling` · `heightfield-lod` ·
`heightfield-raymarching` · `layering-filters-and-masks` · `mask-to-material` · `mesh-extraction` ·
`node-graph-runtime` · `noise-and-warping` · `planetary-precision` · `sea-ice` · `shallow-water` ·
`simulation-time-budget` · `sketch-based-authoring` · `tectonic-uplift` · `tiled-streaming` ·
`virtual-texturing` · `water-closed-vs-open` · `water-optics` · `water-rendering`

## The 34 unverified corrections, by name

`registers/corrections.tsv` has 233 rows. **34 read `verifier=pending`** — one hand wrote the
change and no second hand has re-derived it. A count reads like rounding, so here they are.

**15 are one incident.** The `PD-*-APX` rows — CAUS, DRIV, GPUC, HFLOD, HFRAY, LAYER, NGR, PLANP,
SIMTB, SURF, TAM, TECT, VT, WCVO, WOPT. Commit `11a235d` promised a per-document row for each and
the digest that was to write them never returned; they were recovered four days later in `c234f87`,
verbatim from each applying agent's own report. Nothing in them is invented and none of it is
independently checked. An external rating panel named this cluster as the reason the corpus's
headline jump is not fully earned, and that reading is correct.

**7 are this project's own bookkeeping** — the one-end sweep row, the two audit-file rows, the
pseudocode-register row, the criterion-6 row, the coastal-erosion false-positive row, and
`VB-TRUNCATION`, which records that my own row-writing script silently truncated seven register
fields mid-word.

**6 are Phase C** — `PC1` impact-craters, `PC2` planetary-precision, `PC3` mesh-extraction,
`PC4` river-networks, `PC5` coverage, `PC7` water-closed-vs-open. Verification was scoped by the
owner to the oldest and newest surfaces; these are neither.

**6 are from the verification waves themselves and from the sign-off** — `VA-CI-ANCHORS`,
`VA-CRITIC-1`, `VB-CRITIC-1`, `VB-RATIO`, `CD1`, `SIGNOFF-SP`. Each records a defect found and
fixed; what is unverified is the fix, not the finding.

⚠️ **What `pending` does and does not mean here.** It does not mean unmeasured: every `PD-*-APX`
row names a rig in `rigs/` that re-runs, and the orchestrator re-ran them. It means no hand other
than the one that made the change has re-derived the reasoning around the numbers. On this project
that distinction has mattered: of 26 rows given an independent hostile reader, 10 carried a real
defect — and 2 of 7 disputes raised were themselves wrong and were rejected by a second reader.

## Known issues

**1. The base rate is the headline. Every audited document contained at least one HIGH-severity
defect.** Not one came back clean. Found so far: a live underflow bug that stranded water past a
threshold that scales with terrain elevation; a guard that fired 0 times in 4.8M updates with three
passages depending on it; a `P` tier resting on a printing that stamps "(non-peer-reviewed)" on all
eight pages; a units error that would make a tool never braid; four quotations cut at the clause
that reverses the conclusion; a recommendation that is an exact fixed point of the equation it tells
you to integrate. **The 21 unexamined documents have no reason to be cleaner.**

**2. The tooling has never been audited.** `check.py`, `index.py`, `okf.py`, the CI workflow, the
three registers, both eval files and `SKILL.md` have had no hostile review — and `check.py` is what
every other claim of correctness leans on. Two holes are already recorded in
`registers/guard-proofs.tsv`: `check_section_reach` does **not** catch the case it was built for,
and `approximation` once moved on phrasing alone rather than on new substance. A pass asking *"can
I make this green on a broken corpus?"* is the highest-value work outstanding.

**3. The re-quote pass reaches about 5% of quotations.** `requote.py` locates a quotation in its
artefact and prints what follows, so a silent cut becomes visible. Of 119 checkable quotations it
locates 6; **112 are `UNFETCHED`** because no artefact is cached. That is an artefact-access limit,
not a logic limit — several hosts serve bot challenges, one has an expired certificate. The number
is reported rather than passed over, but it means the corpus's worst recurring defect is still
mostly caught by hand.

**4. Most citations cannot be cross-checked at all.** `propagation` is 16 of 256: only that many
name a section at both the document end and the bibliography end. The guard catches disagreement
where both ends speak; it is silent everywhere else.

**5. Corrections fail at roughly the same rate as findings.** Measured over one working session:
critic claims were refuted or materially corrected about **1 in 4**; the lead's own corrections
about **1 in 3**, with four caught only because an adversarial reviewer read the commit. Reviewer
output arrives with proposed replacement text, and replacement text invents things — three proposed
fixes were refused for shipping a *new* defect, including a sign error and fabricated hardware
labels. **Do not apply a finding here without verifying it.**

**6. 11 coverage rows are planned and unwritten**, listed in `references/coverage.md`. The corpus
names them rather than pretending the map is complete. `resolution-independence` is the one it
calls the most common complaint against tools in this class.

## Next steps, in the order I would do them

⚠️ **This list was written before the 2026-09-05 audit and is reordered here rather than
rewritten, because what replaced it is the more useful record.** Items 1, 2 and 4 are done: the
tooling audit became Phase 0 and closed; the batched audit of 21 documents became 20 per-document
sittings, each with an independent verifier; and `resolution-independence` is written, along with
`shader-craft`. The batching was the wrong unit — a sitting that owns one document and states its
own gates found defects a batch of three would have averaged over.

What remains, in the order I would now do it:

1. **The five sittings still being repaired** — VT + clouds, tiled-streaming + mesh-extraction +
   sea-ice, precision + craters + coastal + sketch, caustics, stratigraphy. Their verifiers have
   reported; the fixes are not yet applied.
2. ~~**Point the eleven rendering documents at `shader-craft.md`.**~~ **Done** — eleven files now
   cite it. (`SKILL.md` said otherwise until 2026-09-15; see the self-description note below.)
3. **The budget-tag migration** — 37+ documents carrying one canonical tag with a `**Tier:` line
   that agrees. Success criterion 6, and the last structural item.
4. **Widen the artefact cache** so `requote.py` covers more than 5%. ⚠️ **This one cannot be done
   by an agent** — it needs artefacts nobody here can fetch.
5. ~~**Raise `approximation`**~~ — **done, 39/40.** ⚠️ But an independent rating panel found the
   metric oversold at the tails: it credits a document for holding both halves *anywhere* in the
   body, and 5 of the 38 put them more than 50 lines apart (`water-optics` 249, `terrain-analysis-masks`
   205). A colocated variant is the honest successor metric.
6. **The `verified:` stamps.** **4 of 40**, signed 2026-09-14 by `human:alexander.pino` on
   `flow-routing`, `terrain-analysis-masks`, `node-graph-runtime` and `stream-power`, after four
   one-page briefs. The stamps were proved to bite: rewording a claim under one goes red,
   re-pointing a locator goes red, editing prose outside the two anchor sections is correctly
   ignored. ⚠️ **Also not available to any agent**, by construction —
   the stamp means a human read the cited work. Phase 0's verifier found that a stamp on a
   bibliography certified nothing at all (the digest hashed the empty string, so one stamp was
   valid on all nine apparatus files); that hole is closed, which makes the stamp worth having and
   still leaves it a human's to give.

## Checking any of this yourself

```
python3 gaia/scripts/check.py              # guard: exit 0, plus every reported metric
python3 gaia/scripts/check.py --selftest   # the fixtures behind the reported metrics
python3 gaia/scripts/check.py --list       # every citation with its tier and locator
python3 gaia/scripts/index.py --check      # index current
python3 gaia/scripts/requote.py --selftest # re-quote fixtures
python3 gaia/scripts/requote.py --cache DIR  # quotations against a local artefact cache
```

The three registers are the primary record and are more reliable than this summary:

- `registers/pseudocode-execution.tsv` — every block transcribed and run, and what the run measured
- `registers/source-findings.tsv` — defects found in the source material
- `registers/guard-proofs.tsv` — each guard, the mutation used to prove it bites, and the guards
  that **do not** hold

## About this file

It is a hand-written summary with no guard behind it, so it can drift from the corpus in a way the
corpus itself cannot drift from `check.py`. Where it disagrees with a register or with a script's
output, **the register and the script are right.** The audit table was reconstructed from commit
history after the scratchpad holding the critique files was lost; the "earlier round" tier is the
least certain line in it.
