# Open items — found by the wave-0 freeze, deliberately not fixed

Modelled on `/home/user/skills/gauntlet/backlog.md`: nothing here is in scope for the wave that
found it. This file is where a finding goes when the frozen registers cannot absorb it — the
registers' row lists are final, so a defect discovered later is recorded here rather than appended
to a `.tsv`.

Ordered by generality: the first items are properties of the whole corpus or the whole guard
suite, the last are single lines. Each carries **what · where found · measurement · why not fixed ·
what would fix it**.

Every measurement below was taken at HEAD `0cdd5b1` and is reproducible from the registers in this
directory.

---

## 1. The numeric census leaves 35% of its own rows undecided

- **What.** `numeric-claims.tsv` classifies each surviving token into `derived` / `external` /
  `illustrative` / `unclassified`. The last bucket is not "clean", it is "no rule fired".
- **Where found.** `registers/numeric-claims.tsv`, class distribution in the header.
- **Measurement.** 1794 of 5152 rows (34.8%) are `unclassified`. They concentrate in
  `12-glacial-coastal.md` (501), `26-hexagonal-grids.md` (290), `28-liquids.md` (151),
  `VALIDATION.md` (112). Inspection shows they are mostly formula exponents and small integers in
  mathematical prose (`n = 3`, `H/3`, `(4/3)`, `(3/7)`, `2N`) plus measured-output table cells.
- **Why not fixed.** Classifying them needs a judgement about whether an exponent in running prose
  is a claim about this code or a restatement of a published relation. That judgement is wave 1's,
  and making it here would have been a fix inside the freeze.
- **What would fix it.** A pass that assigns each `unclassified` row a class using the chapter's own
  citation context — the row list is already frozen, so this is verdict assignment, which later
  waves are permitted to do.

## 2. Only 6 of 30 chapters have any number re-derived by a guard

- **What.** `test_chapter_numbers.py` is the only guard that recomputes a figure a chapter quotes.
  It names six chapters.
- **Where found.** `registers/guard-domains.tsv`, row `test_chapter_numbers.py`.
- **Measurement.** population 30, matched 6, coverage 20.0%. The named chapters are 01, 03, 09, 10,
  12, 26. The 24 unnamed chapters hold the large majority of `numeric-claims.tsv`'s rows.
- **Why not fixed.** Writing 24 chapters' worth of re-derivations is the bulk of the remaining plan,
  not a wave-0 edit.
- **What would fix it.** Per chapter, take that chapter's `derived` rows from `numeric-claims.tsv`
  and add a re-derivation for each; the frozen row list is exactly the worklist.

## 3. The scale contract reaches 19% of the functions it is written to govern

- **What.** `test_scale_contract.py` asserts that atom parameters are not silently in cell units.
  It works off a hardcoded function list.
- **Where found.** `registers/guard-domains.tsv`, row `test_scale_contract.py`.
- **Measurement.** 59 of 309 public functions across `reference-impl/*.py` are covered (19.1%). The
  key is a parameter **name** (`cell_size` / `cellSize`), so a function taking the scale under any
  other spelling is outside the contract even when listed.
- **Why not fixed.** Extending it is a code change to a guard, forbidden in this wave.
- **What would fix it.** Invert the list: enumerate all 309, mark the ones that legitimately take no
  scale, and require every remainder to be checked — the same denominator discipline these
  registers use.

## 4. The slope-units guard is keyed on a substring, so 12 files in its own domain are unreachable

- **What.** `_is_slope_symbol` is `"slope" in name.lower()`. Any spelling of the same quantity that
  does not contain the letters *slope* cannot be flagged, anywhere in the guard's declared domain.
- **Where found.** `registers/guard-domains.tsv`, row `test_slope_units.py`, column `keyed_on`.
- **Measurement.** Declared domain 151 files; 111 contain the literal string `slope` (73.5%). Of the
  40 that do not, 12 discuss the same quantity as `gradient` / `grad` / `dzdx` / `tan(theta)` /
  `repose` / `dip`: `noise.py`, `placement.py`, `hex_grid.py`, `anisotropy_anatomy.py`,
  `references/01-noise.md`, and 7 test files. `np.sin(gradient)` in any of them ships silently.
  The guard's own coverage test asserts only a file-count floor (`>= 100`), never that a spelling is
  reached.
- **Why not fixed.** This is the defect class the whole plan exists to characterise; rewriting the
  key here would destroy the baseline the later waves measure against.
- **What would fix it.** Key on the quantity rather than the name — resolve what each identifier is
  bound to — or, cheaply, extend the symbol test to the enumerated synonym set and re-measure
  coverage against the same 151-file denominator.

## 5. 139 numbers that a module ought to be able to recompute appear in no module and no test

- **What.** Rows with `class=derived` and `verdict=unreproducible`: the chapter presents the figure
  as a property of this system, and nothing in the tree produces it.
- **Where found.** `registers/numeric-claims.tsv`.
- **Measurement.** 139 rows. Concentration: `12-glacial-coastal.md` 82, `28-liquids.md` 14,
  `GALLERY.md` 14, `26-hexagonal-grids.md` 5, `27-engine-data-handoff.md` 4, `VALIDATION.md` 4.
  A further 497 rows are `unclassified` + `unreproducible` and may belong here once item 1 is done.
- **Why not fixed.** Each one needs either a re-derivation or a citation, decided case by case.
- **What would fix it.** Work the 139 in file order; the 82 in `12-glacial-coastal.md` are one
  sitting and would clear 59% of the item.

## 6. Six of eleven reference-impl documents drift unchecked

- **What.** `test_audit_drift.py` reads five of the eleven `reference-impl/*.md` documents.
- **Where found.** `registers/guard-domains.tsv`, row `test_audit_drift.py`.
- **Measurement.** population 11, matched 5 (`ATOM-COVERAGE.md`, `NODE-PARITY-AUDIT.md`,
  `README.md`, `SIMULATION-AUDIT.md`, `VALIDATION.md`). Unchecked: `ARCHETYPES.md`,
  `CANON-COMPARISON.md`, `GALLERY.md`, `GROUNDING.md`, `HYPERREALISM.md`, `REVIEW-BRIEF.md`.
  `GALLERY.md` is partly covered by `test_gallery_doc.py`; the other five are covered by nothing.
- **Why not fixed.** Adding documents to a guard is a guard edit.
- **What would fix it.** Extend the guard's document list to `reference-impl/*.md` by glob rather
  than by name, so the population and the matched set cannot diverge again.

## 7. The audit-drift guard is keyed on an exact section heading

- **What.** `_SCORECARD_HEADING = "## Part 2 — Per-process simulation scorecard"` is a literal.
- **Where found.** `registers/guard-domains.tsv`, row `test_audit_drift.py`.
- **Measurement.** One string. Renaming or re-punctuating that heading in `SIMULATION-AUDIT.md`
  makes every scorecard check find nothing to check — the guard goes quiet rather than red. Note
  the heading contains an em dash, so even a dash normalisation silently disarms it.
- **Why not fixed.** Guard edit.
- **What would fix it.** Assert the heading exists before using it, so its disappearance is a
  failure rather than a skip.

## 8. 18 of 30 chapters are named by no pseudocode-drift tuple

- **What.** `test_pseudocode_drift.py` compares chapter pseudocode constants to module defaults from
  a hand-written list of tuples.
- **Where found.** `registers/guard-domains.tsv`, row `test_pseudocode_drift.py`.
- **Measurement.** population 30, matched 12 (01, 02, 03, 04, 05, 06, 07, 11, 12, 13, 17, 19),
  coverage 40.0%. `registers/constant-pairs.tsv` finds 151 fenced constant assignments across all
  250 fenced blocks; the guard's tuples reach a small fraction of them.
- **Why not fixed.** Guard edit, and the tuples encode real per-constant judgement that cannot be
  generated mechanically.
- **What would fix it.** Use `constant-pairs.tsv` as the worklist: its 81 `diverge` rows are the
  candidates a tuple should exist for.

## 9. 81 stated constants match no module default anywhere

- **What.** `verdict=diverge` in `constant-pairs.tsv`: prose states a value for a symbol the modules
  define, and no definition of that symbol carries that value.
- **Where found.** `registers/constant-pairs.tsv`.
- **Measurement.** 81 `diverge`, against 32 `agree`. Also 98 `chapter_only` (prose states a constant
  for a symbol no module defines) and 514 `module_only` (a shipped default no prose ever states).
- **Why not fixed.** Each row is either a prose error, a module error, or a name collision; deciding
  which is a per-row judgement.
- **What would fix it.** Triage the 81 in verdict-assignment mode. The pairing is name-based, so
  expect a meaningful share to be collisions — that is a verdict, not a deletion.

## 10. 159 chapter-vs-chapter self-inconsistencies, 137 of them on symbols of one or two characters

- **What.** The same symbol is given two different values by two prose or docstring sites.
- **Where found.** `registers/constant-pairs.tsv`, `verdict=chapter_vs_chapter`.
- **Measurement.** 159 rows, of which 137 involve a symbol of <= 2 characters (`n`, `c`, `k`, `H`).
  Single letters are reused across unrelated chapters, so many of those are name collisions rather
  than divergences. The 22 rows on longer names are the high-yield subset.
- **Why not fixed.** Dropping the short-symbol rows would have been the freeze silently discarding
  candidates — the exact failure this plan is built to prevent.
- **What would fix it.** Assign verdicts to the 22 long-name rows first; downgrade the 137 by
  recording a verdict, never by deleting the row.

## 11. Dune `hop`: three sources, three values

- **What.** The saltation length is stated three times and no two agree.
- **Where found.** `references/05-erosion-thermal-aeolian.md:399`; `reference-impl/dunes.py:49`
  (docstring); `reference-impl/dunes.py:20` (default).
- **Measurement.** Chapter says `≈3 cells`. The module docstring says Werner used `~5 cells`. The
  shipped default is `hop=1`. Two rows in `constant-pairs.tsv` carry it: one `diverge`
  (05:399 vs `default:werner_dunes()@20`) and one `chapter_vs_chapter` (05:399 vs the docstring).
- **Why not fixed.** Deciding which of the three is right is a content change to a chapter or a
  module.
- **What would fix it.** Pick the value Werner's model actually uses, set the default to it, and
  make the chapter and the docstring quote the default rather than restating it. Note that the
  docstring value is only visible because register 2 scans a **2-line window**; the statement wraps,
  and a single-line scan reports only a two-way split.

## 12. Lava eruption and solidus temperatures diverge from the module that ships them

- **What.** `19-lava.md` states temperatures the illustrative solver does not use.
- **Where found.** `references/19-lava.md:178-179` against
  `reference-impl/sims_illustrative.py:28` (`lava_flow`).
- **Measurement.** Chapter `T_erupt = 1100`, module default `1400`. Chapter `T_solidus = 980`,
  module default `1000`. Both are `diverge` rows in `constant-pairs.tsv`.
- **Why not fixed.** Content change.
- **What would fix it.** One of the two must move. `sims_illustrative` is the segregated
  no-decisive-oracle tier, so the chapter is the likelier source of truth — but that is a judgement,
  and it is not wave 0's.

## 13. The Terrain Studio 24.7% / 53.8% figure has no implementation behind it

- **What.** A cross-implementation agreement figure quoted in prose for which no such implementation
  exists anywhere in this repo.
- **Where found.** `references/10-primitives-ops-filters.md:609-617`.
- **Measurement.** The paragraph already states the finding: the figure "**has no provenance in this
  repo**", nothing here can re-derive it, and re-running the experiment at the `lacunarity 2.0`
  build the earlier revision claimed measures **24.1% / 53.0%**, not 24.7 / 53.8 — so it was never
  agreement at the precision quoted. The chapter's own reproducible figures are ~29% / ~57% on mean
  |laplacian| and ~9.8% / ~27.2% on high-frequency band energy.
- **Why not fixed.** The prose is already correctly labelled as a stale figure rather than restated
  as agreement, so there is no incorrect claim to remove; what is missing is a decision on whether
  an unreproducible number should be quoted at all.
- **What would fix it.** Either delete the figure and keep the caution about bare percentages, or
  keep it with an explicit "not reproducible here" marker that a guard can assert.

## 14. `09-verification.md:319` still writes `tan(slope)`

- **What.** A failure-mode table row containing the units error the whole `test_slope_units.py`
  guard exists to forbid.
- **Where found.** `references/09-verification.md:319` —
  `| Wetness index → Inf | \`tan(slope) → 0\` on flats | Clamp slope ≥ 0.001 (\`06\`) |`.
- **Measurement.** One line. It is registered in `test_slope_units.py`'s `KNOWN_UNFIXED` tuple, so
  the guard passes with it present; the registry entry records that `09` is outside the file
  ownership of the change that wrote the guard and needs an owner.
- **Why not fixed.** Deliberately owned elsewhere, and the freeze forbids editing a chapter.
- **What would fix it.** An owner for `09`. The adjacent remedy cell is already phrased correctly
  ("clamp slope"), so the fix is to restate the formula and drop the `KNOWN_UNFIXED` row. Note this
  line is also the **positive control** in `falsepositive-seeds.tsv`: fixing it removes the only
  real defect in the frozen prose corpus, and the corpus then needs a new positive control.

## 15. `test_pinned_snippets_appear_near_the_line_they_pin` has never fired

- **What.** A dormant guard row: it is collected and passes, and no input on this corpus ever reaches
  its comparison.
- **Where found.** `reference-impl/tests/test_cited_paths_exist.py:438`.
- **Measurement.** Recorded in the guard's own docstring: 38 citations carry a usable line pin, and
  **zero** quoted spans reach the comparison. It is fixture-tested only.
- **Why not fixed.** The docstring explains why the obvious fix is wrong: admitting any span holding
  `=` or `(` is satisfied by type signatures and typeset maths, and would fail both where they are
  written truthfully. Requiring the span to parse as Python excludes everything currently on a
  pinned line.
- **What would fix it.** A corpus convention that marks a quotation *as* a quotation. Until one
  exists the honest state is a dormant labelled row — but it must be counted as dormant wherever
  guard coverage is totalled, or a reader will read it as evidence.

## 16. Register 2 rejected 104 prose constant candidates for lacking a connective

- **What.** The prose side of `constant-pairs.tsv` requires a connective (`=`, `≈`, `~`, `is`, `of`,
  `at`, ...) between a backticked symbol and the number that follows it. Candidates without one are
  dropped.
- **Where found.** `registers/constant-pairs.tsv` header, `prose:no_connective_between_symbol_and_number`.
- **Measurement.** 171 candidates; 60 kept, 104 dropped for no connective, 7 dropped as citation
  tokens. So 61% of prose candidates were rejected by a single heuristic.
- **Why not fixed.** Loosening it re-admits the citation-year false pairings that the connective rule
  was added to remove (`GROUNDING.md:42` pairing `base` with Perlin **2002**).
- **What would fix it.** Read the 104 by hand once and record which are real. That is the cheapest
  measurement in this backlog and it bounds register 2's largest known gap.

## 17. 514 module defaults are stated nowhere in prose

- **What.** `verdict=module_only`: a shipped numeric default that no chapter, audit document or
  docstring ever mentions.
- **Where found.** `registers/constant-pairs.tsv`.
- **Measurement.** 514 rows, against 151 fenced + 60 prose statements on the other side. The
  documented surface is roughly a quarter of the parameterised one.
- **Why not fixed.** Most are legitimately internal; deciding which deserve prose is editorial.
- **What would fix it.** Nothing, for most. The useful subset is the defaults that appear in a
  function a chapter names — those are the ones a reader will hit and cannot look up.

## 18. Guard files whose only documentation is their test names

- **What.** 11 of the 61 guards have an empty module docstring, so `target_defect_class` in
  `mutation-proofs.tsv` had to be inferred from test-function names.
- **Where found.** `registers/mutation-proofs.tsv` header.
- **Measurement.** 11 of 61 (18%): `test_analytic.py`, `test_diffusion.py`, `test_droplet.py`,
  `test_dunes.py`, `test_flow.py`, `test_isostasy.py`, `test_pipe.py`, `test_runout.py`,
  `test_skill_integrity.py`, `test_streampower.py`, `test_thermal.py`.
- **Why not fixed.** Writing a docstring is an edit to a guard file.
- **What would fix it.** A one-paragraph docstring each, stating the defect the guard exists to
  catch. Until then, wave 2's mutation for these 11 rests on an inference, and its proof is weaker
  than for the other 50 — that difference should be recorded in `observed`, not smoothed over.

## 19. `DEFINITION-OF-DONE.md` landed after the freeze point and is in no register

- **What.** A shipped prose file that did not exist when the wave-0 corpus was fixed, so none of its
  numeric claims has a row in `numeric-claims.tsv`. This is the first exercise of the freeze rule:
  it is recorded here rather than appended to the register.
- **Where found.** `terrain-architect/DEFINITION-OF-DONE.md`, added by commit `aaa376b` on top of
  the freeze point `0cdd5b1` while wave 0 was running.
- **Measurement.** 77 lines, 6 numeric tokens, at least four of which are claims about this repo:
  "a 16k-line knowledge skill with ~60 guard files" (line 6), "manufactured **58%** extra water"
  (line 25), "a units bug once shipped with **1295** tests green" (line 26), "~16k lines of claims
  against ~60 guards" (line 74). The corpus this wave actually scanned is byte-identical between
  `0cdd5b1` and `aaa376b` — `git diff` over `references/`, `reference-impl/`, `SKILL.md` and
  `index.md` is empty — so every count in every register remains correct as stated.
  Note that "~60 guard files" is loose against the measured 61, and "1295 tests" is checkable
  against `test_audit_drift.py`'s live test-count assertion.
- **Why not fixed.** Adding rows for it would break the freeze on the very first day, and the
  register's corpus is named explicitly in its own header — silently widening it is the failure
  mode these denominators exist to prevent.
- **What would fix it.** Wave 1 decides one of two things and writes it down: either the corpus
  definition is extended to `terrain-architect/*.md` and register 1 is **re-derived from scratch at
  a new named HEAD** (not appended to), or the file is declared out of corpus and its four claims
  are checked by hand here. Re-deriving is the honest option if more root-level documents are
  expected; appending is never an option.
