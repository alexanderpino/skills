# Gaia — improvement plan

> **This file is not part of the skill.** Like `STATE.md` and `AUDIT-2026-09-05.md` it sits outside
> `references/`, carries no doctrine, and is invisible to `check.py`. The three meta files divide
> the work: `STATE.md` says what has been checked, `AUDIT-2026-09-05.md` says what was found, and
> this file says what to do about it, in what order, and how to know it worked.

Every item cites a finding ID in the audit (T·, C·, R·, X·, F·, G·, S·). The evidence stays there.

---

## Revision 2 — what five critics changed

The first version of this plan was put in front of five critics before anything was executed:
execution, replacement-fix correctness, guard design, doctrine consistency, prioritisation. Every
claim below marked **verified** was re-checked against the files or re-derived here.

**Three of the plan's own proposed fixes were wrong** — the corpus's 1-in-3 rate, applied to the
plan. Recorded per `guard-proofs.tsv`'s rule, *"recorded rather than quietly replaced"*:

| Proposed fix (v1) | What was wrong | Verified |
|---|---|---|
| X37 — *"subtract only the increment"* | with `w_new` computed from the current deflected `h`, the scheme converges to `(1+T)⁻¹·h₀`, not the flexural surface `(1−T)·h₀`; at long wavelength that is **0.54·h₀ against 0.15·h₀**, 3.6× too high, and the gate *"the ridge survives"* passes it | re-run |
| F4 — `L_scatter ≈ (b_b/(K_d+a))·E·p` | `b_b` already integrates the phase function over the back hemisphere, so `b_b·p` applies the angular shape twice (HG `B(0.924) = 0.017`, a 59× factor), and the denominator is neither the single-scattering `μ_v·K_d + c` nor the QSSA form. **28× too dark** in the audit's own clear-coastal case | re-derived and re-run |
| X51 — `w'_i = (w_i > 0) ? … : 0` | removes the leak at exactly zero and nowhere else; bilinear filtering puts small-but-nonzero weights one texel inside every edge, and the leak persists there. The gate *"28.7% → 0.000%"* measures only the exact-zero case | re-run |

Two more were incomplete (X1's unspecified `eps` is absorbed by fp32 ULP at `t ≥ 5 km`; G1's
one-sided clamp passes `F > 1` on back-facing normals) and two guard designs were unbuildable as
written (T1's default-to-draft makes its own mutation a no-op; T2's body hash collides with the CI
decoys that must stay green). The plan also **dropped 21 audit findings**, including a HIGH (G4) and
a MED-HIGH (G5), carried two dependency graphs that disagreed, gated on a reported metric reaching
zero when its own risk table said it could not, asked the maintainer to write **unsourced
constants** into sourced documents, and claimed not to touch structure while renaming 37 files.

All of it is fixed below. The architecture survived — guard first, pasted code second, agreement
alongside, subtract before add, handoffs before splits — every critic said so.

---

## Goal

Make the skill **trustworthy for the two audiences it names** — a game-engine terrain/water team and
a Gaea-class authoring-tool team — for **real-time and near-real-time physically correct** work, and
take it from the audit's **7.5** to **9+**.

### Success criteria — each with a number and a denominator a second engineer can reproduce

| # | Criterion | Now | Done when |
|---|---|---|---|
| 1 | The six reproduced guard holes are closed | X2, X3, X4, X5, T1, T2 open | each has a `bites` row that goes red **and** goes green with its guard stubbed; the three surfaces the guard cannot see (T3, T4, T8) are `OPEN` rows in `guard-proofs.tsv` and named in `--list` |
| 2 | Every block a reader would paste is correct; every other block runs or is gone | 8 recommendation blocks, 3 broken; 46 body blocks, ≥ 5 documents unregistered | the 8 blocks inside `## Use this` pass their numeric gates; every fenced block has a register row with a **termination** column; 0 fail |
| 3 | The two ends never contradict the body | 9 confirmed inversions | each of the 9 has a `corrections.tsv` row showing both ends were read; `check_repudiation` candidates are all triaged, each false positive recorded with its reason |
| 4 | The engine verdict's three blockers are closed | F1, F3, F4 open | the atmosphere contract carries a unit and a scale; the tick policy is stated; `L_scatter` has a sourced form |
| 5 | The tool verdict is either turned or declared | *"NO, not without three documents"* | `resolution-independence` written; `progressive-preview` and `edit-history` are coverage rows with questions; or `SKILL.md` says the tool half is a declared gap |
| 6 | A reader can tell a document's budget regime from the page | 7 of 37 carry `**Tier:`; 31 carry a budget tag in three spellings | 37/37 carry a `**Tier:` line that agrees with one canonical budget tag, checked |

Not a criterion: item count. 66 rows closed with these six unmet is failure.

---

## Ground rules

1. **Verify before you apply — by two people.** `STATE.md:59-61` records the only process that
   worked: a critic finds, a second agent tries to disprove, the lead re-derives every HIGH.
   Self-verification is what `STATE.md:116` measured failing at 1 in 3, and this plan's first
   version failed at exactly that rate. So: every replacement is **re-derived by A, independently
   disproved-or-confirmed by B, and recorded** in a fourth register,
   `registers/corrections.tsv` — `finding · replacement · derivation · verifier · commit`.
2. **Subtract before you add.** Seven documents sit at 393–446 lines against a 450 cap. Where a
   document needs an addition and has no scheduled subtraction, the addition waits — and the four
   nearest the cap (`surface-and-scale-space` 446, `driver-fields` 438, `seamless-and-periodic` 431,
   `river-networks` 430) have **none scheduled**, so the additions they need (F2, X49) are blocked
   until a sitting finds the room.
3. **Fix agreement alongside, not after.** Zero-line inversion fixes run in parallel with the block
   fixes, not behind 72 re-runs.
4. **Gate a metric before raising it.** Defined for `approximation` below.
5. **Splits come after handoffs.** No split is scheduled; the one candidate is gated.
6. **One change, one gate — of the right kind.** An enforced check gets a `bites` mutation. A
   **reported** metric gets a **fixture set** — it cannot exit red, so `bites` cannot test it
   (`gaia.yml:42-46`). Every gate names the number, the harness, and the register row it lands in.
7. **Every Add names its source first.** No constant or formula enters a document without a
   bibliography entry and a tier, written before the prose. `SKILL.md:44`: a constant from memory is
   *"a `?` wearing a `P`'s confidence."* The v1 plan violated this twice.

---

## Decisions — taken, reversed, and deferred

| Decision | Record |
|---|---|
| **One skill.** `gaia` stays whole | §4e recommended *split, third*; §4h reversed on §4g's shader-gap finding. **The reversal is recorded, not hidden.** §4e's strongest argument — a 178-word description that triggers on breadth, S3's 32-of-37 documents reached by one query — is **unanswered** and deferred with the shader decision. Reconsider only if item 33 places `water-optics.md` cleanly |
| **No filename prefixes** | 37 renames touch 39 coverage rows, 48 `routes_to`, 11 CI paths, ~264 links, ~134 register mentions; §4h itself says a prefix *"adds no new fact"*; and `check.py` stays green on a dangling reference today (a live one exists: `shallow-water.md:212`). **Not scheduled.** `index.py` already groups by axis |
| **Budget as a migration, not a new key** | 31 of 37 documents already carry `authoring-time` (21) / `real-time` (10) / `runtime` (4) / `near-real-time` (1); 5 carry both regimes. A `budget:` key would be a fourth source for a fact with three spellings. **Migrate to one vocabulary; make `**Tier:` agree with it** |
| **`display-transform` is out-of-scope → `physically-based-rendering` §7** | that skill already owns *"color management/OCIO and ACES, physical light units and exposure (EV100) … tonemapping"* (verified). Gaia's half of F1 is the one clause typing its own contract's outputs |
| **G53 is decided: *close*, sequenced after Phase 3** | the shader-vocabulary gap is the largest gap for the primary audience. But `SKILL.md:169` prefers pointing to a sibling over half-covering, and `game-engine-guru` and `physically-based-rendering` own adjacent ground — so the `shader-craft` document is scoped to what neither covers (heightfield-specific: derivatives at LOD seams, VT gradient scaling, max-mip traversal fetch semantics, depth-output direction under reversed-Z) and the **provisional paragraph** in `SKILL.md` lands in week one |
| **`resource:`/`consumes:` front matter — optional, behind the prose** | readers read prose handoff tables, not YAML (prioritisation critic, uncontested). The prose tables (item 33) are the content work. The typed rows are worth having only with a controlled vocabulary — see Phase 5 — and are **put to the maintainer** |
| **Executable content is two things** | 8 blocks inside `## Use this` *are* the recommendation and must be correct; 46 body blocks are the corpus's oracle (`SKILL.md:112-115`) and must **run or go** — never polished. The audit's "executable content: 3" is split accordingly. **Open choice for the maintainer:** make blocks real Python run in CI, or mark them illustrative and drop the run claim — the hand-transcribed middle is where X1's livelock hid behind a register row that measured the wrong property |
| **`SKILL.md` is edited where the audit showed it overstated** | `:103` (a run proves *"implementable and self-consistent"* — X1 is sound and livelocks), `:104` (what `covers` scopes). The four axes, five tiers and router/document split are not touched; the channel table is corrected |
| **`STATE.md` is reordered, and says so** | its next-steps ranked tooling first, then a batched audit of 21 unexamined documents; the fan-out reached 20 of 21, so the batch is replaced by per-document sittings. A reconciliation paragraph and a table refresh land at each phase close |

---

## Status

| Phase | Gate passed | Commit | Verifier |
|---|---|---|---|
| 0 | — | — | — |
| 1 ∥ 2 | — | — | — |
| 3 | — | — | — |
| 4 | — | — | — |
| 5 | — | — | — |
| 6 | — | — | — |

A maintainer fills a row when a phase's *done when* holds. Nothing else marks progress.

---

## Phase 0 — make the guard trustworthy (the six holes, correctly this time)

| Change | Audit | Gate (`bites` unless noted) |
|---|---|---|
| Anchor the index stamp normaliser: `r"^(generated: \{ by: [^,\n]*, at: )[^}\n]*(\}\s*)$"` | X2 | inject a `}`-free block after `at:` → red **(design holds — verified)** |
| Fence closes only at column 0: `line.rstrip() == "---"` | X3 | indented `---` inside a block scalar → `Unparseable` **(holds)** |
| Duplicate key inside `_inline_map` raises, as `:177` already does at top level; unknown keys in a `sources:` row are rejected (`Tier:`, `teir:` beside `tier:` currently pass) | X4 | `{ id: x, tier: F, tier: P }` → red; `teir:` → red |
| **Absent `status:` is a FAIL.** Not "defaults to draft" — deleting `status: draft` from a draft document is then a no-op and the mutation can never go red. `index.py` never defaults it | T1 (corrected) | delete `status:` → red with a unique message |
| **Body hash, reconciled with the decoys.** Make the failure-table heading structural (extend `check_recommendation`'s rule for `## Use this` to it), retire or redirect the `gaia.yml:217` decoy that renames it, and move the `:212` reword decoy's edit outside `## Use this`. Hash the two anchors as a separate `covers_body:` so the message says which half moved; whitespace-normalised. Docstring states that X7/X17/X52-shaped defects sit outside the scope | T2 (corrected) | stamp, mutate one `## Use this` sentence → red; stamp, reword a non-anchor paragraph → green |
| `verified:` needs a non-empty id after `human:` (`"human: "` currently passes, `len 7 > 6`); `verified:` present **requires** `status: stable` (today a draft with a stamp prints **checked**) | G#6 | `by: "human: "` → red; `verified:` on a draft → red |
| **Eval 11 gates the first stamp**: *"Notes that no Gaia document carries `verified:` yet"* goes false the moment one lands. Rewrite it as a check of the index count, not a constant | X20 | the eval must hold before and after a stamp |
| OKF conformance on every document, exempting for apparatus **both** the `sources:` requirement and the marker cross-check — the literal exemption turns the clean corpus red, because `_MARKER` reads `[background]` in `papers-flow.md`'s prose as a citation | 31b (corrected) | delete `type:` from `papers-flow.md` → red (the only bibliography whose deletion is not already caught via a stale index) |
| `requote`: `--selftest` runs `check()` against a fixture directory via a `docs=` parameter, with ALTERED and UNFETCHED cases; exit non-zero when `match + altered == 0` with a cache present (*"nothing checked is not a pass"*); report the quotations excluded by `MIN_QUOTE`, triple-backtick, and the 3-line citation lookback as numbers | X5, X14, G#7 | gut `check()` → `--selftest` red; a cache holding only `README.txt` → red |
| **`bites` attribution.** `expect_red LABEL PATTERN` — the FAIL line must match the named guard's message; and a second pass stubs the named function and requires the row to go **green** (~55 s total). Without this the job cannot tell a mutation caught by the right guard from one caught by a stale index, which is how two rows were already vacuous | X15, G#4 | the two vacuous rows are non-vacuous; every new row passes both directions |
| Register hygiene: re-run the numeric rows; downgrade `guard-proofs.tsv:42` and `:228` to the literal mutation each covers; `papers.md` → real filename in the error text; the dead `note` key populated from continuation lines or dropped; the dead line-cap conditions removed and the bibliography cap decided | X19, T5, T6, T7 | rows match live output; a `--selftest` propagation fixture with a section number on a wrapped line |

**Must not:** widen the parser's accepted subset. Every change narrows what it accepts or checks
what it already accepts.

**Done when:** `check.py` exit 0; `--selftest` green; the **six** holes each have a red-and-green
`bites` pair; T3, T4, T8 are `OPEN` rows; both decoys still green.

---

## Phase 1 ∥ Phase 2 — the document sittings

Phases 1 and 2 run **in parallel**, organised by **document**, not by defect class. One sitting per
document: its broken blocks, its inversions, its subtractions, its corrections that need no new
source, and its `**Tier:` line — under one A/B re-derivation and one read of both ends. The
prioritisation and execution critics both asked for this; the v1 phase structure put 15 zero-line
fixes behind 72 re-runs for no stated reason.

**Phase 1 opens with an enumeration row:** every fenced block in the corpus gets a register row —
document, block, executable yes/no — before anything else. 92 fences across 31 documents; at least
five documents with fences have no row today (`gpu-driven-culling`, `node-graph-runtime`,
`simulation-time-budget`, `tiled-streaming`, `water-closed-vs-open`). Unregistered blocks are
untested by construction. Then add the **termination / step-cap column** (X1b).

### The sittings, by value — HIGH findings closed in bold

| Sitting | Blocks (Phase 1) | Agreement and corrections (Phase 2) | Gate |
|---|---|---|---|
| **`water-rendering.md`** | **G1** — `cosThetaV = saturate(dot(normalize(N), V))`: normalise upstream *and* clamp both ends (a one-sided clamp passes `F > 1` on the 33% of back-facing pixels at 85°); `sqrt(max(sig2, 0))`; guard the horizon intersect. **G2** — store and mip `(A, A²)`, never σ; name an `erf` approximation (not an intrinsic); state that offset-centring is sufficient only while `|μ_A − 1| ≲ 3σ`, else an R32G32F pair | F5 σ-vs-σ² resolved and the comment fixed; X36 the Cox–Munk bound added to the forwarded list; optics #5 the `n²` direction stated both ways | no NaN on a blended unrenormalized normal; `F ≤ 1` everywhere; mip-of-variance tracks true variance |
| **`heightfield-raymarching.md`** | **X1** — relative advance `t = tExitNode·(1 + 2⁻²²)` or advance the DDA cell index (an absolute `eps ≤ 1e-4` is absorbed by fp32 ULP at `t ≥ 5 km`); clamp `tExitNode`; pin registration. **G11** — `SampleLevel` in the divergent loop; `SV_DepthLessEqual` under reversed-Z, `GreaterEqual` under standard; the analytic-derivative rule extended to the material fetch | X11 the relaxed-cone variant re-attributed to Policarpo & Oliveira; X12's (`n²`) note | 0/600 non-terminating **in fp32 at `t ≥ 5 km`** |
| **`tectonic-uplift.md`** | **X37** — carry `w_prev`; `w_new = T·(h + w_prev)` (load from the un-deflected column); `h −= (w_new − w_prev)`. **Not** *"subtract the increment"* from the deflected `h` — that converges to `(1+T)⁻¹h₀`. **X41** radial `k`. **X42** name the load column | **X38** *lower* `Te` | `max|h − (1−T)h₀| < 1e-9` after 10 calls — not "the ridge survives" |
| **`shallow-water.md`** + reference impl | **C2** — name `K·Σf`, and say **flux pass, then depth pass**: every cell's `K` is applied before any cell's inflow is summed (the code does this at `:70,77`; a single-pass reading of *"per step, per cell"* mixes clamped and unclamped neighbours). **R1** — `dt = 0.20·cellsize/√(G·cellsize)`; add a `dt` assertion to `tests/test_shallow_water.py` (CI runs pytest on it; nothing pins `dt` today) | **R1b** — the margin is **2.5×, not 5×**: the two one-way pipes per face each integrate the full head, so the linear scheme's speed is `√(2gA/l)` and 0.502 is exactly the 2-D leapfrog bound `1/√2`. Fix the `√2` in `:120-125`'s linearisation | literal transcription: min depth `−0.000000`, drift ≤ 1.1e-16; checkerboard ~3e-3 |
| **`mask-to-material.md`** | **X51** — the bias must **vanish with the weight** (candidate: `b_i = w_i·(1 + h_i)`, measured 0% leak at `w ≤ 0.01`, continuous); gating on `w_i > 0` fixes exactly zero and creates the C0 step X57 says cannot exist. **G4** — clamp the height-channel LOD; widen `depth` with footprint; a filtering row | **X52** retracted-then-restated width and its two rows; X57 the symptom; **G12** LUT in fp16/R11G11B10F | leak at `w ∈ (0, 0.01]` → 0; `max|ΔA|` across the `w = 0` contour → 0; band width stable across mips |
| **`heightfield-lod.md`** | **G3** — `lerp(sample(mipL), sample(mipL+1), morphK)`, same `morphK` for XZ, height, normal **(design holds — verified)**; re-price the cost cell | C6 the bound stated as a bound | p95 crack below `tau` |
| **`atmosphere-and-aerial-perspective.md`** | — | **X8** the failure row loses the gate its body condemns; G9 the shimmer row's mechanism moves to the depth axis; G10 the mobile apply stated as unmeasured with its range | both ends read; `check_repudiation` no longer flags :384 **for the right reason** (not by adding a dash — one punctuation mark defeats the prototype) |
| **`gpu-driven-culling.md`** | — | **X7** the footprint-mip consequence un-inverted; **G6** the pass topology as a shape, not a slogan; G7 `NonUniformResourceIndex`, the MSAA/conservative-raster caveat; X21 prefix-sum order; X12 the cross-doc rule clause | agrees with bullet 2 at :103 |
| **`wave-models.md`** (subtract only — the add is Phase 5) | — | **X25** the two mis-sourced cost rows deleted; **X26** *phase* speed, group minimum stated; **X27** `q ≤ 1/(z_p·√mss_resolved)` **with the accepted fold fraction `p` named** (0.52 is the 1% value; 0.41 at 0.1%, 0.70 at 5%); X31 the `2 cm` cell carries its `L`; X32 visible repeat = `L_max`; X35 `gcd = 10`; F9's 19.2 ms remark | each re-derived; 2 rows removed |
| **`node-graph-runtime.md`** | — | **X6** the criterion as `cost(hash) < P̂(unchanged)·cost(downstream cone)`, with `P̂` a running per-node hit rate and a structural prior near 1 for clamp/quantise/mask nodes — say it is estimated, not known; **X10** `a + b` ≈ 22 ms, 38× → ~24×; **X17** one prescription for the arithmetic regime; X48; F6 *"preview tier"* defined | each re-derived |
| **`stratigraphy-and-lithology.md`** | — | **X39** rock advection `s = h − U_cum + …`; **X40** the worked arithmetic deleted; X44; X48 | uplift-only with erosion off leaves `K` unchanged. **X39b — time-boxed to two days**: re-run the mesa result; if the rig cannot be rebuilt, add the hedge *"predates the sampler fix, not re-run"* |
| **`seamless-and-periodic.md`** (431 lines — subtract first) | — | **X49** hash period ≥ `P` (an addition — find the room: the X59 4× → 1.7× correction and X60's axis note are line-neutral); **X56** the failure row's 22% → 42%; X54's correction pushed to `noise-and-warping`; X59; X60 | interior repeat at `P = 1024` vanishes; no line added net |
| **`noise-and-warping.md`** | — | **X50** curl as area-preserving only when advected, `det J = 1 + K²·det(Hess ψ)` **(verified to 1e-11)**; X54 the `3/2` rule bounded at 32; C3's sibling note | 51.5% folds at the recommended `K` stated |
| **`driver-fields.md`** (438 lines — subtract first) | — | **F2** `K_Q = K_A·P̄^−m`, units `L^(1−3m)T^(m−1)` **(verified)**; replace the deleted `mm/step` comment with the unit of `P·cellArea` | dimensional; 31.6× at `m = 0.5` |
| **`caustics.md`** — **after** `water-optics.md`'s C1 | — | **X13** name the beam coefficient `c`; **X12** say the caustic layer *replaces* the direct term (an addition — the document never says it); G8's upsample note if the room exists | reads correctly against the corrected C1 |
| `virtual-texturing.md` | — | **G5** `SampleGrad(pool, physUV, ddx(vUV)·vSize/pSize)` and `mip −= log2(feedbackScale)`; the thrash row's second mechanism | two formulas present |
| `volumetric-clouds.md` | — | G8 depth-aware upsample and its opposite reduce | one bullet |
| `tiled-streaming.md` | — | X9 the LRU sentence un-inverted; X22 a `resident → discard` edge | two sentences |
| `mesh-extraction.md` | — | X16 group borders, re-partitioned; X18 *twice* | two sentences |
| `sea-ice.md` | — | X29 one wind convention for the drift pair; X34 the half-width | two sentences |
| `planetary-precision.md`, `simulation-time-budget.md`, `layering-filters-and-masks.md`, `impact-craters.md`, `coastal-erosion.md`, `sketch-based-authoring.md` | — | C3, C4; C5, **F3** (below); X55, X58 (a blank line and a paren); X43, X46; X47; X53 | each re-derived |

**F3, in `simulation-time-budget.md`:** state the policy as *fixed `dt`; accumulate; clamp the
accumulator to `N·dt`; the clamped remainder is sim-time lag, not dropped physics; determinism is a
deterministic function of the tick count with inputs keyed to ticks.* **Not** *"discard beyond"* —
clamping bounds the debt but cannot equalise step count below `1/maxFrameTime`; the v1 gate *"equal
step count across frame rates"* was unreachable (480 vs 600 steps, unchanged). Gate: identical
state after `k` ticks regardless of frame timing.

**`check_repudiation` lands in Phase 2 as a reported metric with a fixture set**, corrected: strip
punctuation in `words()` (`elevation.` ≠ `elevation` defeated the prototype); broaden the
repudiation regex (adds zero corpus false positives — the gram stage is the bottleneck); an
abbreviation guard on the sentence splitter; scan `## Use this` for repudiations too; for the number
signal, take the number **adjacent** to the repudiating phrase and treat a later number in the
sentence as the replacement (else *"used to say 22%; it is 42%"* — the correct fix — is flagged).
**Never a gate.** Its false-positive limit ships in its docstring and `guard-proofs.tsv`.

**Must not:** add a line to any document within 20 lines of the cap until its sitting has found the
room. Rewrite prose that is already right.

**Done when:** criterion 2 holds (every block registered, terminating, the 8 correct); criterion 3
holds (9 `corrections.tsv` rows, each with a verifier); no document crossed 450.

---

## Phase 3 — corrections that need a source

Every row here **names its bibliography entry and tier before the prose is written** (rule 7). The v1
plan gated these on executability and never asked for a source; the corpus has **zero** entries for
Pierson–Moskowitz, JONSWAP, Hasselmann, Gordon, Mobley or Morel.

| Change | Audit | Source and tier to add first | Gate |
|---|---|---|---|
| **C1** — `c/K_d = μ̄_d·(a+b)/(a+b_b)`: in pure water the water-only factor is 1.0–1.2, so the two coefficients agree to within ~25% and **the sign is set by the sun, not the water** (`μ₀` just below a flat surface is 1.00 / 0.85 / 0.76 at zenith 0° / 45° / 60°); in particle-laden water the ratio climbs to tens with `b/b_b`. **Not** *"~0.75 in pure water"* — that hard-codes `μ_d = 0.75`, the deep scattering-dominated asymptote pure water never reaches | Gordon (1989) for the `K_d` approximation, `P` or `P [not-opened]`; Pope & Fry already present | every printed ratio states its `μ_d` |
| **F4** — `L_scatter(0⁻, θ_v) ≈ b·p̃(g, θ_s)·E_d(0⁻)/(K_d + c/μ_v)`, with `b = b_b/B(g)`, `B_HG(g) = (1−g)/(2g)·[(1+g)/√(1+g²) − 1]`, `θ_s` between refracted sun and view, `p̃` normalised to 1 over 4π; or the diffuse budget form `≈ 0.09·b_b/(a+b_b)·E_d(0⁻)`. The renderer still applies `(1−R_int)/n²` on exit. The finite-depth factor becomes `(1 − e^{−(K_d + c/μ_v)z})` | Mobley *Light and Water* (1994) for single scattering and the `f/Q` form, `F` textbook per the corpus's grading of textbooks, or `P [not-opened]` | `b_b` and `phase_g` consumed; the clear-coastal case within 2× of single scattering, not 28× |
| **F8** — `K`'s units on the worked example, routed from `SKILL.md`'s cross-cutting table | `mitchell2021` already present | one parenthetical, one router row |
| The Phase 1∥2 corrections that turn out to need a source are moved here when a sitting finds so | — | — | — |

**The spectrum block (X24, X28) is not in Phase 3.** It cannot fit `wave-models.md` (88 lines of
headroom against PM + JONSWAP + Phillips + spreading + `H_s = 4√m₀` + Hermitian pairing — §4d says
so), and it needs Pierson & Moskowitz (1964) and Hasselmann et al. (1973) as entries first. It is
Phase 5's one split, behind a `wave-spectra` `planned` row.

**Done when:** every row has a `corrections.tsv` entry naming the bibliography id it rests on.

---

## Phase 4 — the structural gaps

| Change | Audit | Gate |
|---|---|---|
| **F1** — type the atmosphere contract's three outputs with **unit, scale and white point**: *scene-referred linear radiance in `W·m⁻²·sr⁻¹`, band-averaged over the three named wavelengths, such that a white Lambertian surface under zenith TOA sun reads `E_sun/π`; pre-exposure; Rec.709/D65 primaries* (or whichever the corpus picks — say which). The v1 clause typed linearity and order and left the number undefined, which is F1's actual failure. Plus a `display-transform` **`out-of-scope`** row → `physically-based-rendering` §7 | F1 | the contract carries a unit a second team can type-check against |
| **F9** — a frame-budget paragraph in `simulation-time-budget.md`, graded `F` and saying so, or one sentence pointing at `game-engine-guru`'s performance section; keep the sourced 19.2 ms remark in `wave-models.md` | F9 | no per-frame recommendation without a cost or a pointer |
| Coverage rows **with their questions and states**: `progressive-preview` `planned` — *"how does a coarse preview refine toward the build without popping, and how is it guaranteed to predict it?"*; `edit-history` `planned` — *"how does undo interact with a content-addressed cache of 67 MB evictable intermediates?"*; `isosurface-extraction` — `planned` or `out-of-scope`, decided, with the reason; `wave-spectra` `planned` — *"which spectrum, sampled at what `N` and `L`, normalised how, with `H_s = 4√m₀` as the acceptance test?"* | F6, F7, X23, X24 | `check_coverage` passes each row's floor with content, not padding |
| Widen `output-contracts` to *"every field a stage hands downstream, with its unit and its space"*; one worked traversal as its acceptance test | F10 | — |
| **Write `resolution-independence`** — `planned` at `coverage.md:50`, *"the most common complaint against tools in this class"*. Then apply it: `hydraulic-erosion`, `thermal-and-aeolian-erosion`, `stream-power`, `flow-routing`, `shallow-water` each state how their parameters scale with cell size | coverage.md:50 | five documents name the scaling of their own parameters |
| **Budget migration**: one vocabulary (`authoring-time` / `real-time` / `near-real-time`, or whatever the maintainer picks), every document tagged, `**Tier:` line on all 37 agreeing with it (`check_axis_agreement`'s pattern), `index.py` groups by it, and a `real-time` document must carry a `COST_UNIT` match | §4g, §4h, G#10 | 37/37; `[both]` everywhere is detectable because the `**Tier:` line must say why |
| `dated-crossover` as a reported metric, scoped to the crossover section, front matter stripped, citation parens and unit suffixes rejected — the fixture set is in the audit (10/15 by regex; the rest need the scoping) | S1 | fixtures |
| **`SKILL.md:103`** → *"produces the printed number for the property the register row names — soundness is not termination"*; **`:104`** states what `covers` scopes; the **provisional shader-scope paragraph** (week one); the cross-cutting row for `K`'s units | §4g, doctrine #3 | the channel table is no longer overstated |
| **The `shader-craft` document** (G53, decided *close*): scoped to what `physically-based-rendering` and `game-engine-guru` do not cover — derivatives at LOD seams, VT gradient scaling and feedback bias, explicit-LOD fetch in a divergent march, depth-output direction under both conventions, the fp16 hazards in G2 and G12 — with its own failure table, and cited from the nine rendering documents | G53 | written to the corpus's standard; the nine documents point at it |
| **`STATE.md` reconciliation**: a paragraph saying the audit reordered its next-steps and why; §Status, §Known issues and the audit table refreshed | doctrine #10 | at each phase close |

**Done when:** criteria 4, 5 and 6 hold.

---

## Phase 5 — handoffs; then the one split

The prose handoff table is the reader-visible artefact and the superset mechanism (§4d). It comes
first. The typed rows are second-order and optional.

| Change | Audit | Gate |
|---|---|---|
| **Generalise the prose `## The handoff` table** to `driver-fields`, `flow-routing` (its `:341` already has the shape, without units), `wave-models`, `simulation-time-budget` — and in doing so **place `water-optics.md`**: if its interface can be stated so completely that the renderer needs nothing else from the simulation axis, the skill seam is real | 33 | each table names quantities with units |
| `check_crossrefs`: every `*.md` named in prose exists — `check.py` is green today on a dangling reference | G#9 | the live dangling reference at `shallow-water.md:212` is caught |
| **Optional, maintainer's call**: `resource:`/`consumes:` rows, one consumer per row (`{ provides, unit, to }` — **parses; verified**), **only with** a `references/quantities.md` controlled vocabulary (a type the guard exempts): every id resolves there, **exactly one provider per id** (`water-rendering.md:32`'s own rule), `to:` must exist, units compared after normalisation. Without the vocabulary a token-equality check flags 5 of 9 rows of the corpus's one *correct* handoff | 31, G#8 | fixtures; reported ratio over the 104 prose pairs, target `≥ 40/104` reciprocal |
| **`wave-models` → `wave-spectra`** — the one split, after its `planned` row and the two spectrum sources exist. Clause 5: it must force a previously implicit quantity into the open (it does — the spectrum→field contract). A one-shot `split.py --from A --into B C` asserts the normalised Symptom-cell set of `B ∪ C ⊇ A` and records it in `guard-proofs.tsv` — not a standing check, and not a row count (padding games a count; Phase 1∥2 legitimately *deletes* rows) | 34, X24, X28, G#11 | clause 5 written down; the block lands with its sources |

**Must not:** split anything else. Rename anything.

---

## Phase 6 — the stamps, and the standing programme

**Stamps last.** T2's digest covers `## Use this` and the failure table, so any later edit there
invalidates a stamp. The first six — `simulation-time-budget`, `shallow-water`, `water-optics`,
`node-graph-runtime`, `heightfield-lod`, `atmosphere-and-aerial-perspective` — are the documents the
critics called best-in-corpus, because verifying an already-good document is cheapest. **A named
person reads each cited work.** No agent output substitutes, by `SKILL.md:104`.

| Change | Gate |
|---|---|
| **The artefact cache.** `STATE.md:105-110` names why it is 6 of 119: bot challenges, an expired certificate — an *access* problem. Either name the mechanism (a maintainer-side fetch with a browser, committed as a private cache; institutional access; author copies) with a target of `≥ 60%` located and every ALTERED resolved — or **state it as unbounded and outside this plan**. The v1 target had no path to its number | the number, or the admission |
| **Gate `approximation`**, defined in the vocabulary the corpus has: a cost figure must cite either a `P` locator that names hardware and resolution, or a `pseudocode-execution.tsv` row — the execution register **is** the "measured here" channel. *"[x] Fig. 2 caption"* is well-formed and not reproducible. Then raise it | rows re-graded before the count moves |
| `registers/corrections.tsv` as a standing register; `STATE.md` refreshed | — |

---

## Dependencies — one graph

```
Phase 0 ──► Phase 1 ∥ Phase 2 (document sittings) ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6 (stamps last)
```

Phase 0 first because T1/X2 change what the index *displays* and the rest gates the first stamp.
1 ∥ 2 because they touch different content and rule 3 forbids putting zero-line fixes behind
re-runs. 3 after 1∥2 because its additions land in the room the sittings make. Stamps last because
every anchor edit before them would have invalidated them.

---

## One week · one month · never

From the prioritisation critic, adjusted for the corrected fixes. ~4 working days for one maintainer.

**Week one** — closes **14 of 32 HIGH**:

1. `water-rendering.md` sitting: G1 (normalise + saturate), G2 as far as `(A, A²)` and the `erf` note
2. `heightfield-raymarching.md`: X1 with the relative advance, in fp32; X1b termination column
3. `tectonic-uplift.md`: X37 with `w_prev`, X38 *lower* `Te`, gate `< 1e-9` — one document, three HIGHs
4. `shallow-water.md` + reference impl: C2 two-pass, R1, the `dt` assertion, R1b 2.5×
5. `mask-to-material.md`: X51 with the bias vanishing with weight
6. The zero-risk inversions: X8, X7, X26, X56 — both ends read
7. F1 with unit, scale, white point; the `display-transform` out-of-scope row
8. F3 as tick determinism
9. **T1 as FAIL + X2** — the two Phase 0 rows a reader sees in the index; their `bites` pairs
10. X58 (a blank line, a paren); the provisional shader-scope paragraph in `SKILL.md`

**Month one** — the remaining sittings, the rest of Phase 0 as one tooling day, Phase 3 with its
sources, Phase 4's rows and `resolution-independence`, `check_repudiation` as a metric. **28 of 32
HIGH by content work; 32 with the tooling day.**

**Never, or not here:**

| Struck | Why |
|---|---|
| Filename prefixes | 37 renames for no new fact; ~500 reference rewrites; a guard that stays green on a dangling link |
| A new `budget:` key | the fact already exists in three spellings on 31 documents — migrate |
| `check_repudiation` or `check_handoff` as a **gate** | reported metrics with known false positives; fixtures, never `bites` |
| Standing failure-row-count check | no split signal; a count is gamed by padding and false-red by legitimate deletion |
| "Raise `approximation`" before its gate exists | it points at the worst-attested content class |
| A second full audit as a plan item | the fan-out reached 20 of 21; sittings replace it |
| Pre-deciding the artefact cache's number without a mechanism | unbounded infrastructure dressed as a gate |

---

## Deferred, with reason

Nothing drops without a decision.

| ID | Sev | Decision |
|---|---|---|
| T3 fabricated-entry surface | MED | `OPEN` row; human work by `check.py:9-12`'s own docstring; `requote` coverage is the only lever |
| T4 `[background]` orphan exit, T8 coverage floors, T9 index banner prose | LOW | `OPEN` rows / one-line `--list` note; do opportunistically |
| S3 trigger reach at the floor, S4 evals behaviour-axis only | obs. | add two positive queries per HIGH document touched in a sitting; eval axis vocabulary constrained in the CI shape check |
| X30 film damping in the pool | MED · PLAUSIBLE | needs a source for the film prefactor before it is written — Phase 3 candidate, not scheduled |
| X33 1-D vs 2-D `k(ω,h)` table | LOW | one sentence when `wave-models.md` is opened for X25–X27 |
| X45 four locators not carrying their claims | MED | Phase 3 — each locator extended or the claim dropped to unsourced; already in the `wave-models`/`coastal-erosion`/`impact-craters`/`tectonic-uplift` sittings |

---

## Risks

| Risk | Mitigation |
|---|---|
| **A correction ships a new defect** — the corpus's rate is 1 in 3; **this plan's v1 rate was 3 in ~20 proposed fixes** | rule 1: two people, one register. The three wrong fixes are recorded above as the reason |
| **The summary is fixed and the body breaks** | each sitting reads both ends; `check_repudiation` re-run as a metric after each |
| **Additions cross the cap** | rule 2 and the per-sitting *must not*; four near-cap documents have no scheduled subtraction and their additions wait |
| **A guard is gameable** — `check_repudiation` cannot tell a surviving retraction from a correctly-landed one; `check_handoff` without a vocabulary flags correct rows | fixtures for the attack each catches; `OPEN` rows for what each misses; neither is a gate |
| **`bites` rows are vacuous** — two already were | every row runs red-with-guard and green-without; message pattern asserted |
| **`check.py` grows unmaintainable** | net new functions: `check_crossrefs`, `check_repudiation` (metric), `dated-crossover` (metric), the budget-tier agreement, optionally `check_handoff`. Five, not eight; no renames, no failure-row count |
| **The plan is executed as a checklist** | the six criteria are the test; the Status table records gates, not items |
| **The stamps land early and are invalidated** | Phase 6 is last, by construction |

---

## What this plan touches — honestly

It **edits `SKILL.md`** at `:103`, `:104`, the cross-cutting table, and one scope paragraph. It
**writes two documents** (`resolution-independence`, `shader-craft`) and **one split**
(`wave-spectra`), each behind a `planned` row with its question. It **adds five bibliography
entries** (Pierson & Moskowitz, Hasselmann et al., Gordon, Mobley, and whichever `shader-craft`
needs), each at the tier it honestly holds. It **adds one register** (`corrections.tsv`) and one
column (termination). It **migrates** 31 budget tags to one vocabulary and **adds** a `**Tier:` line
to 30 documents. It changes **~8 guard behaviours** and adds **~5 functions**. It touches **~75
sentences across ~25 documents** and deletes several. It does **not** rename a file, split the
skill, change an axis or a tier, or raise `approximation` before gating it.

Estimated surface, counted from the tables above rather than guessed: 66 rows; ~75 sentence-level
edits; 9 block corrections; 92 block registrations; 2 new documents and 1 split; 5 bibliography
entries; 37 tier lines; 1 simulation re-run (time-boxed); 6 human source-reads.

---

## Target: 9+ / 10

| Dimension | Now | 9 means | Reached by |
|---|---|---|---|
| Stated constants | 9 | hold | Phase 3's rule 7 |
| **The 8 recommendation blocks** (was: "executable content") | 3 | all correct under numeric gates | Phase 1 sittings |
| **The oracle** (46 body blocks) | — | every fenced block registered with a termination column; 0 fail | Phase 1 enumeration |
| **Recommendations and failure tables** | 5 | 9 inversions closed with both-ends rows; 37/37 `**Tier:` | Phases 2, 4 |
| Provenance as a system | 9 | hold | Phase 0 |
| **Provenance in practice** | 6 | X25/X45 fixed **and** the artefact cache either reaches ≥ 60% or is declared unbounded | Phase 3, Phase 6 — **the honest limit** |
| **Guard engineering** | 5 | six holes, red-and-green pairs | Phase 0 |
| Coverage and routing | 8 | rows with questions; budget migrated; `dated-crossover` | Phase 4 |
| **Audit state** | 5 | six documents carry `verified:` by a named human | Phase 6 — **no agent can do it** |
| **Usability** | 7 | F1/F3/F4/F9 closed; `resolution-independence` written; `shader-craft` written | Phases 3, 4 |

Phases 0–4: ~8.5. Phase 5–6, with `shader-craft`, a sourced `L_scatter`, and the six stamps: **9+**.
The two items that no plan row can force are the cache (access) and the stamps (a human). Both are
named as the limit, not hidden in a standing programme.
