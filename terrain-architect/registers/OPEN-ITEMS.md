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

## ⚠️ Status, reconciled against the tree at HEAD `8fe5688`

**This file was itself stale.** Seven items were closed by the guard wave and never marked, which
is the same defect the file exists to catch: a record that no longer matches what it records.
Reconciled by running the guards, not by reading the list.

| item | now | evidence |
|---|---|---|
| 4 | **CLOSED** | the slope guard is no longer keyed on a substring. `_census()` → 351 trig calls, 351 adjudicated, 331 decided without the word `slope` |
| 6 | **CLOSED** | `test_audit_drift`'s domain is `REF.glob("*.md")`; `AUDIT_DOCUMENT_COUNT = 11`, was 4 literals |
| 7 | **CLOSED** | same rewrite; the em-dash heading was also shown to fail LOUDLY (26 failed), not silently |
| 21 | **CLOSED** | `test_scale_contract` consults the dead-parameter census instead of crediting a declaration |
| 26 | **CLOSED** | both rows corrected in `guard-domains.tsv`'s AMENDMENT block |
| 28 | **CLOSED** | the `test_slope_units.py` row is rewritten, with what it replaced written down |
| 30 | **CLOSED** | the three prose test-count claims are requoted from the disk oracle: 620 functions |

Items **1, 2, 3, 5, 8, 9, 10, 12, 13, 15, 16, 17, 18, 19, 23** remain open and are the substance of
criteria A and F, which `DEFINITION-OF-DONE.md` records as **accepted fails, not passes**.

Items **11/27, 20, 22, 24, 25, 29** are **CLOSED** by wave 6. Suite after it: **1665 passed, 5
skipped**; census **0 dead parameters**; figures **14/14**.

⚠️ **Three of those six items contained a measurement that was FALSE**, and in each case the agent
sent to act on it refused and checked instead of complying:

* **#24** located the defect at `graph_demo.py:214`'s `p.get("method", "fill")`. That fallback was
  **unreachable**: `build_graph:303` and `build_scene_graph:377` each passed
  `params={"method": "fill", …}` explicitly, so fixing the named line would have closed the item
  while moving no figure, no test and no terrain. Verified against `8fe5688`. All three sites flipped.
* **#27** claimed "every actual call site passes `hop=3`, so the shipped default of 1 is used by
  nothing." `gallery.py:166` names no `hop` at all and ran on the default — which is exactly what
  made the default load-bearing, and what made `gallery.png` drift when it changed.
* **#20** said only test files blocked the deletions. False for two of four: `deposit_fill` was
  called positionally from `graph_demo.py:402`, `archetypes.py:350` and `analysis.texture_base`,
  and `hydrology.water_surface` had an unlisted **non-test** caller at `hero.py:191`, inside the
  producer of `hero.png`. A **fifth** dead parameter (`hydrology.water_depth`) went uncounted.

That is three waves running where this directory's own measurements, not the code, were the thing
most in need of checking.

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

## 20. Four dead `cellsize` parameters that only a non-owned test file stops us deleting

- **What.** A public function declares a parameter no line of its body reads. The class is already
  confirmed twice on this tree (`render.material_rgb`'s `shade` and `cellsize`), and the code wave
  built the full AST census for it. Six survivors were found; two were fixed; four remain, all of
  them the same parameter, `cellsize`, and all four blocked by a call site in a test file the code
  wave does not own.
- **Where found.** `reference-impl/tests/test_render.py`,
  `test_no_public_function_declares_a_parameter_it_never_reads` and its
  `DEAD_PARAMETER_EXEMPTIONS` table, which carries the reason and the blocking call for each.
- **Measurement.** 44 modules, 314 public functions and public methods, 1320 parameters, 6 dead.
  Fixed: `halfar_anatomy.sia_at_cfl(n)` (deleted; `cellsize` made keyword-only because the one call
  site passed `n` positionally in front of it, so a bare deletion would have slid `n = 121` into
  `cellsize = 12000.0`) and `analysis.peaks(cellsize)` (deleted; `radius` and `eps` made
  keyword-only). Remaining, with the blocker:
  - `aeolian.yardang(cellsize)` — `tests/test_gallery_doc.py:90` passes `cellsize=_CELLSIZE`.
  - `tectonics.fault_weakness(cellsize)` — `tests/test_gallery_doc.py:94` passes it.
  - `analysis.deposit_fill(cellsize)` — second POSITIONAL slot; `tests/test_archetypes.py:151`
    passes it positionally, as do `graph_demo.py`, `archetypes.py` and `analysis.texture_base`.
  - `hydrology.water_surface(cellsize)` — a REQUIRED positional slot; `tests/test_hydrology.py`
    lines 13, 28, 39 and `tests/test_gallery_doc.py:99,100` all pass it positionally.
- **Why not fixed.** Deleting a parameter is an API change, and each of these four needs a
  simultaneous edit to a test file outside the code wave's ownership. For `deposit_fill` and
  `water_surface` the deletion is also the `material_rgb(masks, cellsize, palette)` hazard exactly:
  the slot is positional, so a bare removal does not raise, it hands the next argument to the wrong
  parameter. Implementing them instead is not a free alternative — see item 21.
- **What would fix it.** One patch per function, deleting the parameter and making everything after
  it keyword-only so a stale positional call raises instead of landing in the wrong slot, plus the
  matching one-line edit at each call site listed above:
  `aeolian.yardang(h, wind, soft_mask, *, ... seed=0)` and `tests/test_gallery_doc.py:90` loses
  `cellsize=_CELLSIZE`; `tectonics.fault_weakness(shape, *, ... seed=0)` and
  `tests/test_gallery_doc.py:94` the same; `analysis.deposit_fill(h, *, radius=3)` with the four
  call sites dropping their second positional argument; `hydrology.water_surface(bed, discharge,
  *, ...)` and `hydrology.water_depth(bed, discharge, **kw)` with five call sites updated.

## 21. `test_scale_contract` credited a declaration as a fact, and two atoms were passing on it

- **What.** `test_every_atom_is_scale_explicit` asked `"cellsize" in signature(fn).parameters` and
  treated the answer as evidence the atom is resolution-aware. A parameter that is declared and
  never read satisfies that exactly, so the `08` scale contract was being met, for two atoms, by an
  argument nothing reads. This is now fixed — the guard asks the dead-parameter census whether the
  parameter is READ — but the underlying atoms are not.
- **Where found.** `reference-impl/tests/test_scale_contract.py`, and the two new entries in
  `PIXEL_OR_CALLER_SPACE`.
- **Measurement.** 2 of the atoms in the coverage manifest: `aeolian.yardang` and
  `tectonics.fault_weakness`. Both are exempted on their real grounds (index-space geometry) rather
  than on the dead parameter. Mutation-proved: making `erosion_thermal.thermal_erosion` stop
  reading its `cellsize` now turns the guard red; laundering the same parameter through an alias
  does not.
- **Why not fixed.** Making the parameter real is not a wiring change in either case.
  `yardang`'s lane frequencies `freq_along=0.018` and `freq_cross=0.11` are per-CELL, so a
  per-metre reading needs both defaults re-baselined — a constant change that belongs with chapter
  16, not with the module. `fault_weakness`'s `width=4.0` is a Gaussian half-width in cells; read
  as metres it is sub-cell at any realistic resolution and the function would silently return a
  uniform `K`, which is worse than the dead parameter.
- **What would fix it.** A chapter-16 decision on the yardang lane wavelength in metres, and a
  chapter-02 decision on fault damage-zone width in metres (a few hundred metres is the usual
  figure), then thread `cellsize` through both and delete the two exemptions.

## 22. `07` recommends Ulichney tiles twice and nothing implements them

- **What.** The one in-scope capability the chapters recommend that has no implementation at all.
  `07` names Ulichney void-and-cluster tiles as the recommendation for dense ground cover and again
  as the tiling answer ("Preferred"), and `scatter.py` ships `poisson_disk` (Bridson),
  `scatter_by_density`, `jittered_grid` and `rule_based` — so the shipped ground-cover story is the
  option `07` itself ranks second and calls "not true blue noise".
- **Where found.** `references/07-scatter.md:149` and `:175`; enumerated as
  `ulichney-ground-cover` in `reference-impl/tests/test_graph_demo.py`'s
  `RECOMMENDED_CAPABILITIES`, pinned in `KNOWN_UNREACHABLE`.
- **Measurement.** 9 recommended capabilities enumerated from 38 recommendation-language lines
  across `references/*.md`; 8 reachable from the shipped graph, 1 not. Both sides of the gap are
  pinned by `test_ulichney_tiles_are_still_recommended_and_still_absent`, so implementing it turns
  that row red and forces the census to be re-adjudicated rather than quietly closed.
- **Why not fixed.** A void-and-cluster tile generator is a new atom with its own oracle (tileable
  by construction, blue-noise spectrum, deterministic), not a wiring fix, and the atom set is
  frozen in `test_atom_coverage.IMPLEMENTED`.
- **What would fix it.** `scatter.ulichney_tile(n, seed)` plus a spectral oracle, a row in
  `IMPLEMENTED` and in `ATOM-COVERAGE.md`, and promotion of the census row from `KNOWN_UNREACHABLE`
  to a real reachability row.

## 23. The recommendation sweep cannot find the recommendation it was built for

- **What.** The mechanical population for criterion G2 was extracted by searching `references/*.md`
  for recommendation language. `03:247` recommends the hybrid MFD/D8 router in the words "this
  costs almost nothing and is what most good terrain tools do" — no recommendation word anywhere in
  the sentence — so the extraction rule provably misses the very instance the criterion was written
  around. The row is carried by hand and labelled as hand-added.
- **Where found.** `reference-impl/tests/test_graph_demo.py`, the denominator block above
  `RECOMMENDED_CAPABILITIES`.
- **Measurement.** 38 lines found mechanically; 29 excluded in eleven counted buckets; 9 in scope;
  1 added by hand. A rule that misses one known member of its own population has an unknown miss
  rate on the rest.
- **Why not fixed.** The honest response to a lossy extraction rule is to report the loss, not to
  widen the regex until the tests pass — a widened regex would fold in the 29 excluded lines and
  the census would stop being finite.
- **What would fix it.** A read of all 30 chapters by a human or a model, marking every sentence
  that ranks one shipped option above another, and a comparison of that list against these 9.

## 24. `03` recommends breach/fill as the DEFAULT; the shipped graph still defaults to fill

- **What.** `flow.breach_fill` now exists and is selectable from the demo graph, which is what
  criterion G2 required. But `03:101` does not merely offer it, it calls it "the right default for
  terrain generation", and `graph_demo`'s fill node still ships `method="fill"` — as `_area_fn`
  still ships `method="d8"` against `03:247`'s recommended hybrid. Reachable is not the same as
  default, and two chapters currently recommend a default the demo does not take.
- **Where found.** `references/03-flow-routing.md:101` and `:247`; `reference-impl/graph_demo.py`,
  the `filled` and `area` node parameters.
- **Measurement.** On a 60x60 noisy plain with one 60 m crater, `priority_flood_fill` raises 1029
  cells above the input and `breach_fill(max_depth=10)` raises 476 — the crater still fills to a
  lake, the noise pits are carved out. That is the lakes-vs-canyons trade `03` describes, measured.
- **Why not fixed.** Changing a shipped default changes every downstream figure and every
  behavioural expectation in the demo's guards; it is a judgement about what the demo is for, not a
  defect. Recording it is the point.
- **What would fix it.** A decision, written down in `graph_demo.py`, either flipping both defaults
  to the chapter's recommendation or stating why the demo deliberately ships the simpler one.

## 25. `crater_anatomy.py` has no build guard, and the guard costs three lines in a non-owned file

- **What.** `VALIDATION.md` rung 4 stakes a corrected morphology on this figure — a grazing crater
  is deeper UP-RANGE — and the figure was the only artifact in the tree carrying that claim with no
  build guard in any environment. It could stop building, or start drawing the deepest point
  down-range again (the exact defect rung 4 corrected), and nothing would fail.
- **Where found.** `reference-impl/crater_anatomy.py`; `reference-impl/VALIDATION.md:317-318`.
- **Measurement.** `build()` now takes an output path and returns `(canvas, facts)`; on the shipped
  parameters it reports `deepest_col=216` against `centre=230`, i.e. up-range, with
  `ellipticity=2.00` and `diameter_m=1446.6`. `tests/test_anatomy_figures.py` already carries the
  module-level `pytest.importorskip("PIL")`, so the guard costs one import and two asserts.
- **Why not fixed.** `tests/test_anatomy_figures.py` is not in the code wave's ownership. The
  module-side half is done; only the guard row is outstanding.
- **What would fix it.** Append to `reference-impl/tests/test_anatomy_figures.py`:

  ```python
  def test_crater_anatomy_builds_and_still_draws_the_uprange_asymmetry(tmp_path):
      """VALIDATION.md rung 4 stakes a corrected morphology on this figure: a grazing impact is
      deeper UP-RANGE (first contact / peak energy), not down-range. The figure was the only
      artifact carrying that claim with no build guard, so it could silently stop building or
      silently flip back to the skipping-stone intuition rung 4 corrected."""
      import crater_anatomy
      img, facts = crater_anatomy.build(str(tmp_path / "crater_anatomy.png"))
      assert img.size[0] > 900 and img.size[1] > 700
      assert facts["deepest_col"] < facts["centre"], (
          "the trajectory cross-section's deepest point is no longer up-range (%d vs centre %d); "
          "that is the rung-4 defect returning" % (facts["deepest_col"], facts["centre"]))
      assert facts["ellipticity"] > 1.5    # a grazing cavity is elongated, not circular
  ```

## 26. Two frozen register rows now describe module text that has moved

- **What.** The code wave was asked to make `glacier.py` and `dunes.py` self-consistent. Both were
  fixed on the DOCSTRING side, never the shipped value, precisely so that
  `test_pseudocode_drift.KNOWN_DIVERGENCES` — which pins `K_g=8e-4` and `hop=1,` in the module
  source under a staleness rule — keeps holding. But `constant-pairs.tsv` also records the
  docstring side of the dune case, and that text has changed.
- **Where found.** `registers/constant-pairs.tsv:412`, verdict `chapter_vs_chapter`, recording
  `docstring:dunes.py hop@49 = 5`.
- **Measurement.** `dunes.py`'s docstring no longer says "Werner used ~5 cells" as a bare claim; it
  now enumerates all four statements of `hop` (05:412 says ~5, 05:399 says ≈3, the docstring said
  5, the signature ships 1) and says which is which. The row's *finding* is unchanged and in fact
  strengthened; only the quoted text moved.
- **Why not fixed.** The registers are frozen and this wave may fill verdicts, not edit rows.
- **What would fix it.** A later wave re-quotes the docstring side of row 412, or notes that the
  divergence it records is now stated in the module rather than merely implied by it.

## 27. `05` states the dune saltation hop as two different numbers, thirteen lines apart

**Supersedes item 11**, which records the same constant as a three-way split. It is a four-way
split and the fourth statement is inside one chapter; item 11's remedy ("pick the value Werner's
model actually uses") cannot be carried out until `05` stops giving two of them.

- **What.** The dune `hop` was described to the code wave as a three-way split (`05` says ≈3, the
  `dunes.py` docstring says ~5, the signature ships 1). It is a FOUR-way split, and the fourth is
  inside one chapter: `05:412`'s Werner pseudocode block fixes `L = saltationHop  # ~5 cells,
  fixed`, while `05:399`'s runnable-reference note says the hop is "≈3 cells". So the chapter
  contradicts itself before any module is consulted.
- **Where found.** `references/05-erosion-thermal-aeolian.md:399` and `:412`.
- **Measurement.** Four values for one constant: 5 (05:412), 3 (05:399), 5 (dunes.py docstring,
  now rewritten to enumerate all four), 1 (`werner_dunes`'s default).

  ⚠️ **CLOSED, and this paragraph's own measurement was FALSE.** It said "Every actual call site in
  the repository passes `hop=3` … so the shipped default of 1 is used by nothing." Checked:
  `gallery.py:166` calls `werner_dunes(sand, 300, seed=SEED, wind=(0, 1))` and names **no** `hop`,
  so it ran on the shipped default of 1 — and the committed `gallery.png` was built that way. That
  one call site is what made the default load-bearing. `tests/test_dunes.py:86` also passes `hop=1`
  explicitly. Only `capability_grid.py:317` and three rows of `test_dunes.py` pass 3. The
  recommendation to adopt 3 rested entirely on the false claim, so it was discarded.

  **Resolved as 5**, from the source rather than from local usage. Kok, Parteli, Michaels & Karam
  2012, *The physics of wind-blown sand and dust*, Rep. Prog. Phys. **75** 106901 §3.2.2, on
  Werner 1995: *"A sand slab on the surface is chosen at random and moves downwind to a new lattice
  site l (typically equal to 5) sites away."* `05:412` had been citation-faithful all along; the
  unsourced `≈3` at `05:399` and the shipped `1` were the outliers. All four statements now read 5,
  and the wavelength claim is demonstrated rather than asserted: over 3 seeds on a 32×192 domain,
  mean spectral centroid **28.4 → 37.0 → 44.9 cells** for hop 1 → 3 → 5, with no seed overlap
  between 1 and 5 (+58 % wavelength, +67 % relief).

  The `werner-saltation-hop` divergence row is **retired and replaced**, not merely deleted: a
  `BLOCK_CONSTANTS` row pins the chapter's fenced block against the shipped default, a new
  `test_chapter_note_quotes_the_shipped_hop` pins `05:399`'s **prose** (which the old register could
  never see — `_fenced()` reads fenced blocks only, which is exactly how the chapter's
  self-contradiction survived a guard file built to catch drift), and two behavioural guards prove
  the agreement is not cosmetic.

  **Consequence, open:** `gallery.png` no longer reproduces from its producer, because `gallery.py`
  was the caller relying on the default. 13 of 14 figures still reproduce.
- **What would fix it.** `05` must state ONE value. The recommendation from the code side: make
  both places say **~3 cells**, since 3 is what every call site in this repository actually runs and
  what `05:399` already tells a reader; then raise `werner_dunes`'s default from 1 to 3, delete the
  `werner-saltation-hop` divergence row and add a normal pinned pair in its place. If instead `05`
  keeps Werner's ~5, the module default should become 5 and `05:399` must be corrected — but the
  one outcome that must not survive is two numbers in one chapter.

---

## 28. `guard-domains.tsv`'s row for `test_slope_units.py` now describes a guard that no longer exists

- **What.** The frozen row records `keyed_on = identifier containing the SUBSTRING 'slope'`,
  `population 151 / matched 111 / 73.5%`. That guard has been replaced: the default is inverted,
  so the key is the trig CALL and every call in the domain is a defect unless its argument is
  positively shown to be an angle (numeric/degree/π literal, a symbol registered for that file, or
  an `atan`/`arctan`/`radians` wrapper). The row is frozen and its freeze rule allows a wave to
  "correct a population/matched figure or sharpen a note", but not to change what the column
  means, so the correction is recorded here instead of overwritten there.
- **Where found.** `registers/guard-domains.tsv` line 92; the replacement is
  `reference-impl/tests/test_slope_units.py`.
- **Measurement.** New figures, asserted in-file by
  `test_the_scan_adjudicates_every_trig_call_in_the_domain`: 151 files in the declared domain, 66
  of them carrying a trig call, 347 trig calls, 347 adjudicated (identity holds — nothing is
  skipped), and **327 of the 347 (94.2%) decided without the word `slope` appearing anywhere in
  the argument**, against 0 for the old key. Both guards were loaded side by side from commit
  `d8dbd8c` and the current tree and called on the same strings: `np.sin(s)`, `np.sin(gradient)`,
  `np.tan(dzdx)`, `np.sin(repose)`, `np.sin(np.hypot(dzdx, dzdy))`,
  `np.sin(slope + np.arctan(aspect))`, `np.sin(np.degrees(np.arctan(slope)))`,
  `np.tan(maxSlope)` in `analysis.py`, and a 497-character argument — old = 0 hits on all nine,
  new = 1 hit on all nine.
- **Why not fixed.** The register is frozen and three other agents are writing to this directory in
  the same wave; rewriting a frozen row's `keyed_on` is not a figure correction.
- **What would fix it.** In the next wave, replace that row's `keyed_on` with "any trig-family
  call whose argument is not a numeric/degree/π literal, a symbol in ANGLE_REGISTER for that file,
  or wrapped in atan/arctan/atan2/radians/deg2rad", and its coverage with the reach denominator
  above (347/347 adjudicated, 327 word-independent). The full proof set is in
  `registers/mutation-proofs.partial-slope.tsv`.

---

## 29. `test_atom_coverage.py` still carries its own private text model, which disagrees with the shared one

- **What.** `reference-impl/tests/_textscan.py` now holds the one fence model, the one Python
  prose model, the identifier pattern and the completeness matcher, and `test_slope_units.py` has
  adopted it. `test_atom_coverage.py` has not: it keeps `_FENCE = r"^```[^\n]*\n(.*?)^```"`
  (column 0 only), `_IDENT`, `_pattern`/`_complete` and `_strip_py_comments`.
- **Where found.** `reference-impl/tests/test_atom_coverage.py:68` (`_IDENT`), `:70` (`_FENCE`), `:140` (`_pattern`), `:194` (`_complete`), `:199` (`_strip_py_comments`).
- **Measurement.** Over the 44 Markdown documents in the scanned corpus, the shared model and the
  column-0 model disagree on 31. Four of those are substantive: `03-flow-routing.md` (+67 chars),
  `12-glacial-coastal.md` (+428), `13-climate-ecosystem.md` (+130), `26-hexagonal-grids.md`
  (+296) — whole fenced blocks that `test_atom_coverage.py` cannot see because they are indented
  under a list item (`03:693`, `12:293`, `12:2095`, `13:461`, `26:345`). Its
  `test_landform_is_documented_as_a_routine` and `test_pseudocode_header_matches` search
  `_fenced(...)` only, so a routine documented inside one of those blocks reads as undocumented.
  The other 27 differences are exactly one trailing newline per block (`-1` char × block count)
  and are not behavioural. The shared model agrees with this file's own previous `lstrip` model on
  all 44 documents, line for line. `complete_pattern` and `blank_py_prose` were checked to be
  byte-identical to that file's `_pattern` and `_strip_py_comments` over the corpus.
- **Why not fixed.** `test_atom_coverage.py` is owned by another agent, running concurrently.
- **What would fix it.** Four substitutions in that file, no behaviour change except the four
  chapters: `_fenced(text)` -> `"\n".join(b.text for b in _textscan.fenced_blocks(text))` (or
  `_textscan.fenced_text(text)`); `_IDENT` -> `_textscan.IDENT`; `_pattern`/`_complete` ->
  `_textscan.complete_pattern`/`complete_match`; `_strip_py_comments(src)` ->
  `_textscan.blank_py_prose(src, path)`. Its `test_fenced_reads_pseudocode_only` fixture keeps
  passing as written.

## 30. The wave's own new guard rows pushed three prose test-count claims out of band

- **What.** `test_audit_drift.test_every_recountable_claim_matches_the_tree` recounts the suite size
  quoted in `README.md`, `VALIDATION.md` and `REVIEW-BRIEF.md` against the tree and allows 10 %
  drift. Adding guard rows — which is what this wave was for — moved the real count past that band.
- **Where found.** `reference-impl/tests/test_audit_drift.py:874`; the quoted figures in
  `reference-impl/README.md`, `reference-impl/VALIDATION.md` (twice) and
  `reference-impl/REVIEW-BRIEF.md`.
- **Measurement.** `def test_` functions in `reference-impl/tests/`: **620** now; **566** at the
  freeze point `23bceef`. 54 were added by this wave, 17 of them by the code lane
  (`test_render.py`, `test_graph_demo.py`, `test_scale_contract.py`). `README.md` and
  `VALIDATION.md` quote **530**: 6.8 % off at 566 (green), 14.5 % off at 620 (red) — so those two
  rows were pushed red BY the wave, jointly, and no single lane's additions account for it.
  `REVIEW-BRIEF.md` quotes **334**, which was already 41 % off at the freeze point: that row was
  red before anyone touched anything and is a separate, older staleness.
- **Why not fixed.** Requoting is a prose edit in three files no code-lane owns, and any number
  written while other lanes are still adding rows is stale before it lands. The 620 figure is only
  correct as of this run.
- **What would fix it.** Once the wave's guard rows are all in, one pass requoting the three
  documents against a single measured run — and, for `REVIEW-BRIEF.md`, a decision about whether a
  parenthetical suite size is worth carrying at all, given it has been wrong by 41 % since before
  the freeze.
