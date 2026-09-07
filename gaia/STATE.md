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
| Documents | **39** written, 13 planned, 6 explicitly out of scope (52 topics in scope) |
| Bibliography | 225 entries, 225 cited, 0 orphaned |
| Adversarially audited | **37 of 39** — see the reconciliation below |
| Verified corrections | **143** rows in `registers/corrections.tsv`, every one signed by an independent verifier |
| Guards | `check.py` exit 0 · `--selftest` green · `index --check` current · `requote --selftest` green · CI `bites` 33 red + 4 green |
| Phase 0 | **closed** 2026-09-07 — the guard layer, verified by mutation under `bash -e` |

Reported metrics, none of them enforced:

| Metric | Value | What it means |
|---|---|---|
| `approximation` | **7/39** | documents stating *both* how good a recommendation is and what it costs |
| `locators` | 187/264 (71%) | citations naming a section, equation or page rather than a topic |
| `propagation` | **17/283** | citations naming a section at *both* ends, so the two can be cross-checked at all |
| `reach` | 16/206 | body sections sharing no word with `## Use this` or the failure table |
| `unread` | 29/283 | citations that *declare* the source was never opened here |
| `crossrefs` | **1/227** | shared magnitudes that DISAGREE across documents — new, and it found a live one on its first run |

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
2. **Point the eleven rendering documents at `shader-craft.md`.** The document exists and nothing
   cites it, so a reader still meets each hazard in isolation. G53 is not closed until they do.
3. **The budget-tag migration** — 37+ documents carrying one canonical tag with a `**Tier:` line
   that agrees. Success criterion 6, and the last structural item.
4. **Widen the artefact cache** so `requote.py` covers more than 5%. ⚠️ **This one cannot be done
   by an agent** — it needs artefacts nobody here can fetch.
5. **Raise `approximation`** — 32 of 39 documents still give an error or a cost, not both. Supply
   the missing half from sources; the metric has already been caught mismeasuring its own fix once.
6. **The `verified:` stamps.** 0 of 39. ⚠️ **Also not available to any agent**, by construction —
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
