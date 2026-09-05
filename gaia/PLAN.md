# Gaia — improvement plan

> **This file is not part of the skill.** Like `STATE.md` and `AUDIT-2026-09-05.md` it sits outside
> `references/`, carries no doctrine, and is invisible to `check.py`. The three meta files divide
> the work: `STATE.md` says what has been checked, `AUDIT-2026-09-05.md` says what was found, and
> this file says what to do about it, in what order, and how to know it worked.

Every item below cites a finding ID in the audit (T·, C·, R·, X·, F·, G·, S·). The evidence stays
there; this file carries only the decision, the change, the gate, and the order.

---

## Goal

Make the skill **trustworthy for the two audiences it names** — a game-engine terrain/water team and
a Gaea-class authoring-tool team — for **real-time and near-real-time physically correct** work.

Success is measurable, and it is not "all 53 items closed":

| Criterion | Now | Done when |
|---|---|---|
| The guard cannot be made green on a broken corpus by any attack in the audit | 6 reproduced holes | every hole has a `bites` mutation that goes red |
| Every pseudocode block the corpus ships runs and terminates as written | 3 broken (X1, X37, C2) + 1 in the reference impl (R1) | execution register carries a termination column; 0 blocks fail it |
| `## Use this` and the failure table never contradict the body that corrects them | ≥ 9 instances | `check_repudiation` reports 0 |
| The light chain has typed endpoints | 0 hits for exposure / display transform | one clause and one coverage row (F1) |
| A physical quantity crossing a document boundary carries its unit | 81% of edges one-way; 0 `resource:` rows | `check_handoff` reports the reciprocal ratio and it rises |
| A reader can tell a document's budget regime | 7 of 37 declare a tier | `budget:` tag on every document, checked |

---

## Ground rules

Taken from the corpus's own record and this audit's experience. They are not optional.

1. **Verify before you apply. Every time.** Reviewer corrections here fail at roughly 1 in 3, and
   this audit added three of its own to the count: a harness bug, a predicted blow-up that was
   sloshing, and a `resource:` schema in §4h that the corpus's own parser rejects (nested list inside
   an inline map — `okf.py` forbids it by design). Re-derive the replacement, run the block, parse
   the front matter, *then* edit.
2. **Subtract before you add.** Seven documents sit at 393–446 lines against a 450 cap. The material
   to cut is already identified (X25's mis-sourced rows, X52's retracted-then-restated paragraph,
   X40's arithmetic). Deletions first; the room for additions is exactly there.
3. **Fix agreement before volume.** The summary-vs-body inversions cost zero lines and remove defects
   from the two places readers trust. They go before any additive item.
4. **Gate a metric before raising it.** `approximation` at 7/37 points at the worst-attested content
   class in the corpus. A cost figure gets provenance discipline before the count is pushed.
5. **Splits come after handoffs.** A document or skill boundary switches off the bidirectional
   guards across it. The typed handoff exists first, or the split converts visible defects into
   invisible ones.
6. **One change, one gate.** Nothing lands without the mutation, fixture or re-run that proves it.
   A guard never seen to fail is not known to be a guard — that is the repo's standing rule.

---

## Decisions taken — and what is explicitly *not* being done

| Decision | Why | Audit |
|---|---|---|
| **One skill, not `gaia` + `gaia-rasterizer`** | seven bidirectional guards operate on one skill's `references/`; the split severs them across the 17 edges where every handoff defect lives; and a rendering skill carved out today inherits the shader-vocabulary gap wholesale | §4e, §4g, §4h |
| **Prefix by axis if at all, never `rasterizer-`/`physics-`** | seven documents are genuinely both, including `shallow-water.md`, where the corpus's own thesis lives; a filename holds one fact | §4h |
| **Audience and budget as `tags:`, not filenames** | multi-valued; one source of truth; `budget: [offline, per-frame]` is the machine-readable form of the `**Tier:` line 30 documents lack | §4g, §4h |
| **Typed handoff as OKF `resource:` front matter, one consumer per row** | the key is spec-recommended and unused; flat rows parse, nested lists do not | §4d, §4h |
| **`approximation` is not raised until gated** | rule 4 | §4c |
| **The corpus's structure, tiers, routing and doctrine are not touched** | none of it is broken; every defect is a sentence, a constant, a line of code or a missing row | §5 |

---

## Phases

Each phase has a scope, a gate, and a list of things it must **not** do. Phases 0–2 are sequential
— each is a precondition of the next. Phases 3–6 can interleave once 2 is green.

### Phase 0 — Make the guard trustworthy

Everything downstream trusts `check.py`. It has six reproduced holes, and `STATE.md` already ranked
this first. Nothing else lands until this is green, because a corrected document behind a gameable
guard is a corrected document nobody can prove is corrected.

| Change | Audit | Gate |
|---|---|---|
| Anchor the index stamp normaliser to one line | X2 | `bites`: inject a `}`-free block after `at:` → red |
| Fence at column 0; duplicate-key rule inside `_inline_map` | X3, X4 | `--selftest` fixtures for both; `bites` for each |
| Missing `status:` means `draft` in both scripts | T1 | `bites`: delete `status:`, regenerate index → red |
| Body hash folded into `sources_digest()` (`## Use this` + failure table) | T2 | `bites`: stamp, mutate the body → red |
| Run the OKF conformance block on every document; exempt only the `sources:` requirement for apparatus | 31b | `bites`: delete `type:` from a `papers-*.md` → red |
| `requote --selftest` exercises `check()` against a tmpdir cache; `main()` returns 1 on ALTERED; an empty cache directory is treated as no cache | X5, X14 | gut `check()` → `--selftest` red |
| Make the two vacuous `bites` mutations non-vacuous (regenerate the index first; assert on the expected message) | X15 | delete the named guard → the mutation must go green, proving it was testing that guard |
| Re-run the register's numeric rows; downgrade `guard-proofs.tsv:42` and `:228` from `PROVEN` to the literal mutation they cover | X19 | rows match live output |
| Hygiene: `papers.md` → the real filename in the error text; drop the dead `note` key or populate it; remove the dead line-cap conditions and decide the bibliography cap | T5, T6, T7 | trivial |

**Must not:** widen the parser's accepted subset. `okf.py`'s restriction is the feature; every fix
here narrows what it accepts or checks what it already accepts.

**Done when:** `check.py` exit 0, `--selftest` green, every audit attack in §1 and §4b has a `bites`
row that goes red, and the decoys still stay green.

### Phase 1 — Fix what a reader would paste

The executable content. Four blocks are broken in ways reading cannot see; three more carry NaN or
crack hazards a shipping engineer found on first contact. Each fix is re-run before it lands.

| Change | Audit | Gate |
|---|---|---|
| `t = tExitNode + eps` on the skip branch; clamp `tExitNode`; pin the texel-registration convention | X1 | 0/600 non-terminating, from 63% |
| Make the flexural deflection a state variable; subtract only the increment | X37 | ten calls on a 3000 m ridge leave the ridge |
| Replace the reference CFL with the scheme's own `A/l`; fix or qualify the citation that vouches for it | R1, R1b | checkerboard amplitude ~3e-3, not ~2e-1 |
| Name the post-clamp sum in the pipe block | C2 | literal transcription: min depth `-0.000000`, drift ≤ 1.1e-16 |
| Normalise before biasing; gate on `w_i > 0` | X51 | zero-weight leak 28.7% → 0.000% |
| `max(…, 0)` under `pow` and `sqrt`; guard the horizon intersect | G1 | no NaN on a blended unrenormalized normal |
| Store and mip `(A, A²)`, never σ; offset-centre for fp16; name an `erf` approximation | G2 | mip-of-variance tracks true variance; the block compiles |
| `height = lerp(sample(mipL), sample(mipL+1), morphK)`; same `morphK` for XZ, height, normal; re-price the cost cell | G3 | p95 crack below `tau` |
| Add a **termination / step-cap** column to the execution register | X1b | the raymarching row says which property it tested |

**Must not:** rewrite prose around the blocks. The blocks change; the explanations that are already
right stay.

**Done when:** every block in `pseudocode-execution.tsv` has been re-run under the new column, and
the reference implementation's own invariant tests still pass.

### Phase 2 — Fix agreement

Zero-line changes. The summary contradicts the body that corrects it, or one document keeps what a
sibling retracted. This is the corpus's most-recorded defect shape, found nine times this pass, and
it now has an instrument.

| Change | Audit |
|---|---|
| Land `check_repudiation` as a reported metric with fixtures (3-grams, code fences stripped, the number-retraction signal), and the false-positive limit in its docstring | 30 |
| The atmosphere failure row that ships the gate its body condemns | X8 |
| The seamless failure row that keeps 22% where the body says 42% | X56 |
| The HiZ footprint-mip consequence, inverted one bullet below its correct statement | X7 |
| The wave-speed floor that the same document's damping table breaks | X26 |
| The `Te` remedy that points the wrong way | X38 |
| The retracted-then-restated transition width, and its two failure rows | X52 |
| The caustic double-count fix that does not fix the double-count | X12 |
| The three-way arithmetic-regime contradiction | X17 |
| The sea-ice drift pair that mixes two wind conventions | X29 |
| The `3/2` lacunarity rule corrected in one document and not the other | X54 |
| The dilation-by-`R` sentence a sibling already states as `N·R` | X55 |
| The Cox–Munk anisotropy bound that never reached its consumer | X36 |
| The inverted ULP-bound sentence, the false "same 7.8 mm" cross-reference, the pipe-model-in-a-frame contradiction | C3, C4, C5 |
| The six bibliography count, in two files | S2 |

**Must not:** add a sentence anywhere. If a fix needs new words, it belongs in Phase 3.

**Done when:** `check_repudiation` reports 0 and the cross-document pairs above have been read at
both ends.

### Phase 3 — Fix what is wrong

Content corrections that change a claim. Every replacement is re-derived first (rule 1), and the
subtractions land before the additions (rule 2).

**Subtract:**

| Change | Audit |
|---|---|
| The cost-table row that cites a whitecap paper for wave-packet cost against the document's own disclaimer; the Gerstner accuracy row cited to a wave-particle paper outside its locator | X25 |
| The stratigraphy timestep arithmetic that only appears to predict its own runs | X40 |
| The `"c` typically runs 5–20× `K_d"` range and the sentence that inherits it | C1 |
| The impossible `a + b` timing and the 38× headline resting on it | X10 |

**Then correct:**

| Change | Audit | Gate |
|---|---|---|
| `c/K_d` as mechanism and span: ~0.75 in pure water to tens in turbid, governed by single-scattering albedo | C1 | pure-water Pope & Fry values must give 0.75–0.90 |
| The cutoff criterion as `cost(hash) < P(unchanged) × cost(downstream cone)` | X6 | the rule must permit the clamp in the document's own example |
| Rock advection in the stratigraphy sampler; **then re-run the mesa negative result** | X39, X39b | uplift-only with erosion off must not change `K` |
| `K_Q = K_A·P̄^−m`, its units, and the deleted `mm/step` comment | F2 | dimensional; 31.6× at `m = 0.5` |
| The timestep debt policy: clamp accumulated frame time, discard beyond | F3 | equal step count across frame rates |
| Curl noise as area-preserving only when advected: `det J = 1 + K²·det(Hess ψ)` | X50 | 51.5% folds at the recommended K |
| The hash period must be ≥ `P`; a 256-entry table caps the tile at 256 | X49 | interior repeat at 1024 must vanish |
| The phase-vs-group floor; the choppiness clamp as `≈ 0.54/rms-slope` per cascade; the `2 cm` floor carrying its `L`; the visible repeat as `L_max` | X26, X27, X31, X32 | each re-derived |
| The σ-vs-σ² choice, resolved and stated, and the comment fixed | F5, optics #7 | the shader form names which reading it commits to |
| The remaining MED/LOW corrections in §4b | X9, X16, X18, X21, X22, X41–X48, X53, X57–X60, C6 | each re-derived |

**Add (last, into the room the subtractions made):**

| Change | Audit | Gate |
|---|---|---|
| The spectrum block: PM / JONSWAP / Phillips with `α, γ, σ_a, σ_b, ω_p`, one spreading function, the `k⁻⁴` convention, `H_s = 4√m₀`; Hermitian pairing and its failure row | X24, X28 | the document's own "sample a spectrum into a grid" becomes executable |
| `L_scatter` supplied or explicitly handed off: `≈ (b_b/(K_d+a))·E_d(0⁻)·p(g,θ)` | F4 | `b_b` and `phase_g` are consumed, not only declared |
| `K`'s units on the stream-power worked example, routed from `SKILL.md`'s cross-cutting table | F8 | |

**Must not:** add a line to any document that is within 20 lines of the cap until its subtractions
have landed. `surface-and-scale-space.md` has four.

**Done when:** every replacement has a re-derivation recorded in a register row, and no document has
crossed 450.

### Phase 4 — Close the structural gaps

The buildability findings. Two are one clause each; the rest are coverage rows that turn undeclared
holes into declared ones — the corpus's own discipline for a gap it has decided about.

| Change | Audit | Gate |
|---|---|---|
| The atmosphere contract's outputs typed as scene-referred linear radiance, pre-exposure; a `display-transform` coverage row | F1 | the exposure grep stops returning 0 |
| A frame-budget paragraph: what fraction of a frame terrain + water + sky may claim; and the 19.2 ms remark | F9 | the one water cost figure is no longer unremarked |
| Coverage rows: `progressive-preview`, `edit-history`, volumetric isosurface extraction; and the term "preview tier" defined where it is used | F6, F7, X23 | `SKILL.md:147` reports them as decided, not unclaimed |
| Widen `output-contracts` to every field a stage hands downstream, with unit and space; one worked traversal as its acceptance test | F10 | |
| Write `resolution-independence` — planned, unwritten, the most common complaint against tools in this class | coverage.md:50 | each erosion document applies it to its own parameters |
| `budget:` and `audience:` tags on every document, checked; `dated-crossover` as a reported metric | §4g, §4h, S1 | 37/37 declare a budget regime |

**Must not:** write a shader-level document yet. That is Phase 6's decision.

### Phase 5 — Handoffs, then structure

The §4d/§4h work. The typed handoff is the superset mechanism; the guard on it is what makes any
later split safe. **Phase 5 is a precondition of any split, and no split is scheduled.**

| Change | Audit | Gate |
|---|---|---|
| `resource:` front matter on every document that hands a quantity across — **one consumer per row**, `{ provides, unit, to }` — and the reciprocal `consumes:` row on the consumer | §4h (corrected schema) | `okf.py` parses every row |
| `check_handoff`: the two ends must name the same quantity; report the reciprocal ratio like `propagation` | 31 | starts at 19% reciprocal; must rise |
| Failure-row preservation: count rows per document, a split's halves must sum to ≥ the original | 32 | nothing counts them today |
| Generalise the handoff to `driver-fields`, `flow-routing`, `wave-models`, `simulation-time-budget` — and in doing so **place `water-optics.md`** | 33 | if its interface can be stated completely, the seam is real |
| Axis prefixes (`gen-`, `sim-`, `render-`, `arch-`) — only with the check that prefix matches tag | 31c | third source of truth, checked |
| *Then, and only if item 33 places `water-optics.md`:* the document splits — `wave-models` → `wave-spectra` first | 34 | clause 5: the split must force a previously implicit quantity into the open |

**Must not:** split anything before `check_handoff` reports. Not a document, not the skill.

### Phase 6 — The decision, and the standing programme

| Change | Audit |
|---|---|
| **Decide the shader-vocabulary gap.** `SampleGrad`, `SampleLevel`, `mediump`, `denormal`, `NonUniformResourceIndex` are 0 hits. Either close it — one `shader-craft` document owning precision, derivatives, sampling, early-Z semantics and divergence — or state in `SKILL.md` that the rendering axis stops at algorithm-and-pass and name what a team needs beside it | G53 |
| Audit the remaining unexamined documents to the same standard; update `STATE.md`'s table | P4 |
| Gate `approximation` (a cost figure needs a reproducible provenance), then raise it | rule 4 |
| Widen the artefact cache so `requote.py` reaches more than 6 of 119 quotations — the only instrument aimed at the fabrication surface | T3, P4 |

---

## Dependencies

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► { Phase 3, Phase 4, Phase 6 } interleave
                                    └─► Phase 5 ──► (splits, if ever)
```

Phase 0 is first because a fix behind a gameable guard cannot be proven. Phase 1 is next because the
broken blocks are what a reader pastes today. Phase 2 before 3 because agreement fixes cost nothing
and 3's additions land in the room 2 and 3's subtractions make. Phase 5 gates every split.

---

## Risks

| Risk | Mitigation |
|---|---|
| **A correction ships a new defect** — the corpus's rate is ~1 in 3, and this audit's own §4h schema did it | rule 1; every replacement is re-derived or parsed before it lands, and recorded |
| **Fixing the summary breaks the body** — a failure row rewritten without re-reading the paragraph it summarises | Phase 2 reads both ends; `check_repudiation` re-run after every edit |
| **Additions push documents over the cap and force splits before Phase 5** | rule 2; the *must not* clause in Phase 3 |
| **The new guards are gameable** — `check_repudiation` cannot tell a surviving retraction from a correctly-landed one; `check_handoff` can be satisfied by an empty row | each ships its limit in its docstring and a `bites` mutation for the attack it *does* catch; a false-positive row goes in `guard-proofs.tsv` OPEN |
| **`check.py` becomes unmaintainable** — eight checks added to a 1,400-line file | each check is one function with one fixture set, like the existing ones; no shared state |
| **The plan is executed as a checklist** — 53 items closed, corpus not better | the success criteria at the top are the test, not the item count |

---

## What this plan does not do

It does not touch the corpus's four axes, its provenance tiers, its routing, or its doctrine. It
does not split the skill. It does not raise `approximation`. It does not write a shader-level
document — it schedules the decision. Every change is a sentence, a constant, a line of code, a
front-matter row, or a coverage row.

Total surface, honestly estimated: **two parser functions, ~8 guard functions, one CI job, ~40
sentences across ~25 documents, ~6 coverage rows, and one decision.**
