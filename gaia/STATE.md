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
| Documents | **37** written, 11 planned, 4 explicitly out of scope (48 topics in scope) |
| Bibliography | 214 entries, 214 cited, 0 orphaned |
| Adversarially audited | **16 of 37** |
| Never examined | **21 of 37** |
| Guards | `check.py` exit 0 · 72/72 fixtures · `requote` 6/6 · index current |

Reported metrics, none of them enforced:

| Metric | Value | What it means |
|---|---|---|
| `approximation` | **7/37** | documents stating *both* how good a recommendation is and what it costs |
| `locators` | ~70% | citations naming a section, equation or page rather than a topic |
| `propagation` | **16/256** | citations naming a section at *both* ends, so the two can be cross-checked at all |
| `reach` | 17/193 | body sections sharing no word with `## Use this` or the failure table |
| `unread` | 26/256 | citations that *declare* the source was never opened here |

## Audit state, per document

Three tiers. Nothing here is "verified" in the strong sense — no document carries the `verified:`
header that would mean a human read every cited work.

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

1. **Audit the tooling** (issue 2). Highest value, because everything downstream trusts it.
2. **Audit the 21 unexamined documents**, in batches of three, subject critic + adversarial
   verifier, and an architect pass for anything on Rendering, Architecture or Simulation. Risk
   order by how heavily a document has already been edited: `mask-to-material` (4 register rows),
   `sketch-based-authoring` (3), `shallow-water` (3). Promote `node-graph-runtime` (longest
   unaudited document, on the axis everything else assumes) and `simulation-time-budget` (it tells
   you how to spend a frame, and cost figures have been found wrong by 1000× and by four orders of
   magnitude elsewhere in this corpus).
3. **Widen the artefact cache** so `requote.py` covers more than 5%.
4. **Write the 11 planned rows**, starting with `resolution-independence`.
5. **Raise `approximation`** — 30 of 37 documents still give an error or a cost, not both. Do it by
   supplying the missing half from sources, not by loosening the pattern; the metric has already
   been caught mismeasuring its own fix once.

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
