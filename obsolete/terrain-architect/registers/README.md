# registers/ — the frozen enumerations

Built in wave 0 of the closure plan, at HEAD `0cdd5b1` on branch
`claude/swimming-pool-voronoi-render-m22g6r`. Commit `aaa376b` landed on top of `0cdd5b1` while
this wave was running, adding `terrain-architect/DEFINITION-OF-DONE.md` and nothing else; the
scanned corpus is byte-identical across the two commits (`git diff 0cdd5b1 aaa376b` over
`references/`, `reference-impl/`, `SKILL.md`, `index.md` is empty), so every figure below stands.
The new file is out of corpus and is logged as item 19 of `OPEN-ITEMS.md` rather than added to a
register — the first exercise of the freeze rule. Nothing in this directory fixes anything. Every file
here is a census: a row list computed once, so that the passes after it are finite.

**The rule that makes the plan terminate, and it applies to every file below: later waves may only
assign or correct a verdict. They may not add a row, remove a row, widen a scan, or substitute an
input.** A finding that has no row goes to `OPEN-ITEMS.md`. This is the whole point — an
enumeration that grows while it is being worked is the unbounded critic loop wearing a new hat.

**Every register carries a denominator in its header**, because a census built by substring
extraction over ~16k lines of prose is precisely the artefact class that has failed in this repo
before. A denominator states the population found, how many rows it became, and a counted breakdown
of every exclusion. Where the accounting is exact the header prints an IDENTITY line and whether it
holds. A register whose exclusions do not sum has traded completeness away silently, and the
identity line is what makes that visible instead of invisible.

---

### `numeric-claims.tsv` — every numeric claim in shipped prose

Enumerates one row per **numeric token** surviving exclusion across the 43 shipped prose files
(`references/*.md` 30, `reference-impl/*.md` 11, `SKILL.md`, `index.md`; 20 776 lines), each with a
class (`derived` / `external` / `illustrative` / `unclassified`) and a provisional verdict
(`guarded` / `unguarded` / `unreproducible`). **Denominator:** 13 033 numeric tokens found, 5 152
became rows, 7 881 excluded across eleven counted categories (`fenced_code` 1 304, `chapter_xref`
3 066, `bibliographic` 2 803, `okf_frontmatter` 266, `list_index` 217, `heading_number` 60,
`figure_panel_index` 54, `url_doi_hash` 45, `anchor_link` 29, `math_display_block` 19,
`math_inline` 18); 5 152 + 7 881 = 13 033, identity holds. The unit is the token and not the claim
on purpose: a range like "5–11 m" emits two rows sharing one `claim_text`, because merging is the
step at which a claim can disappear unseen. The `unclassified` bucket is 1 794 rows and is reported
as undecided, not as clean.

### `constant-pairs.tsv` — chapter constants against module defaults, and against each other

Enumerates every constant stated in shipped prose — in fenced pseudocode **and** in running text —
paired against every numeric default in `reference-impl/*.py`, and against every other statement of
the same symbol. **Denominator, prose side:** 250 fenced blocks, 1 896 fenced lines, 1 304 numeric
tokens inside them (the same 1 304 that register 1 excludes as `fenced_code`, so the two registers
reconcile); 151 became constant assignments and 1 153 were excluded across five counted categories;
151 + 1 153 = 1 304, identity holds. Prose side: 171 candidates, 60 kept, 111 rejected in two
counted categories, one of which reuses register 1's exclusion map verbatim so the two registers
cannot disagree about what a citation is. **Denominator, module side:** 298 symbols with a numeric
default, 98 with a docstring-stated value, 514 never mentioned in prose. 884 rows. The
`chapter_vs_chapter` verdict exists because a chapter↔module table cannot see a symbol that
contradicts itself: dune `hop` is stated as 3 in `05`, as 5 in `dunes.py`'s docstring, and shipped
as 1 — and the docstring statement is only visible because the scan uses a **2-line window**, since
this corpus hard-wraps.

### `guard-domains.tsv` — what each guard is keyed on, and what evades it

One row for every one of the 61 guard files in `reference-impl/tests/`, with the scan domain,
population, matched count, coverage, and — the column that matters — `keyed_on`: the literal thing
the scan keys on, and therefore the spelling that walks past it. **Denominator:** 61 guard files,
classified mechanically after stripping module docstrings and comments so that prose *about*
reading does not count: 9 `text_or_source_scanner`, 3 `introspection_scanner`, 1 `binary_reader`,
48 `numeric_or_behavioural_only`; 9 + 3 + 1 + 48 = 61, identity holds. All 61 get a row so no guard
sits outside the freeze; the 48 non-scanners carry population 0. Per-guard denominators are files
or symbols in the declared domain versus how many the key can actually reach — which is how this
register records that `test_slope_units.py` reaches 111 of 151 files because it is keyed on the
substring `slope`, and that 12 of the 40 it cannot reach discuss the same quantity as *gradient*,
*dzdx* or *tan θ*.

### `mutation-proofs.tsv` — stubs, one per guard, for wave 2 to fill by execution

61 rows, one per guard file. `target_defect_class` is filled; `mutation`, `decoy` and `observed`
are deliberately empty because wave 2 fills them **by running things**, not by predicting. The
distinction the column enforces: `target_defect_class` is what the guard *exists for*, taken from
its module docstring where it has one (50 of 61) and from its test-function names where it does not
(11 of 61) — it is not "any defect this guard happens to catch". A mutation drawn from the second
list proves only that a guard is non-vacuous; a mutation drawn from the first proves it does its
job. **Denominator:** 61 rows == 61 guard files; the three shared helpers (`tests/asserts.py`,
`tests/inputs.py`, `reference-impl/conftest.py`) are excluded and counted, none containing a
`test_*` function.

### `falsepositive-seeds.tsv` — the frozen inputs for criterion C

11 rows covering four guard families that partition all 61 guards (9 prose-scan + 3 introspection +
1 binary-artifact + 48 numeric-field = 61, identity holds), each naming the exact inputs a
false-positive pass must use. Six rows name **shipped prose line ranges rather than arrays**,
because the worst false positive in the session this plan closes was a guard that flagged correct
English: `05`'s sentence "`sin(slope) > sin θ` makes `wet` come out low" is right, and it was
flagged for containing none of fourteen hardcoded negation cues. Random arrays cannot reproduce
that failure mode at all. **Denominator:** 111 frozen prose lines in the units-keying corpus across
chapters 05, 06, 17 and three regions of 09; 683 backticked spans in the citation corpus; 412 lines
in the audit corpus; 860 in the scope corpus; 9 synthetic generators from `tests/inputs.py`; and the
seed sets already in use in this repo (`default_rng` {0,1,2,3,5,7,11,36}, `RandomState` {0,3,7}).
The units-keying corpus contains one real defect on purpose — `09-verification.md:319` — as a
positive control: a pass that comes back entirely clean has shown the guard is off, not that it is
precise.

### `OPEN-ITEMS.md` — everything deferred

Modelled on `gauntlet/backlog.md`, ordered by generality, each entry carrying **what · where found ·
measurement · why not fixed · what would fix it**. Seeded with what the census found — the
`unreproducible` and `diverge` populations — plus the three items the plan named: the Terrain Studio
24.7 / 53.8 figure with no implementation behind it, `09:319`'s `tan(slope)`, and the dormant
`test_pinned_snippets` row. It has no denominator because it is not a census; it is the overflow,
and it is the only file in this directory that is allowed to grow.
