# Terrain Studio — progress

Where the work stands. **`BACKLOG.md` holds findings, decisions and defects; this file holds
position** — what shipped, what the gates measured, what is next.

Updated as work lands. If this disagrees with a commit message, the commit wins.

---

## Suite coverage — corrected 2026-07-31

`npm run verify` runs **12 of 75** oracle files (it points at `_verify_all_canyon.js`, the Canyon
suite). Use `node scripts/sweep-oracles.mjs` for all of them.

    node scripts/sweep-oracles.mjs                  every oracle, one line each
    node scripts/sweep-oracles.mjs _verify_x.js     a subset

Current record: **74/74 standalone oracles green** on 2026-07-31
(`_verify_all_canyon.js` is the one aggregate file excluded by the sweep). The all-oracle run first
reported 71/74: the production PWA gate had reused a stale test-mode preview, shape scan found two
misplaced annotations in the hydraulic apron, and deep zoom exposed an unconditional global-height
camera guard. A fresh production preview plus targeted reruns closed all three; the hydraulic
camera-guard load gate was rerun separately after the zoom correction. Failing output is retained
in `.sweep-logs/`.

## Now

**PHASE 0 — DELIVERY RECOVERY, 2026-08-03.** The programme was audited against the source rather
than against its own status documents, and the two abandoned branches were recovered. Plan of
record: `~/.claude/plans/distributed-squishing-feigenbaum.md`.

### Measured ground truth at the start of this pass

Every story in all ten sprint documents was audited against the tree, then adversarially re-checked.
**3 of 55 stories had shipped** (S1.0, S1.1, S1.2), four were thin partials where an existing node
overlaps a contract without satisfying it (S4.8, S4.9, S4.10, S5.1), and the rest were absent —
including all of S2, S3, and S6 through S10. About **405 of 417 points remained**.

Three findings changed the plan:

1. **There is no project save/open.** File menu is New / Import heightmap / Export heightmap;
   `localStorage` holds three UI preferences. But S2.2, S8.5, S8.6, S9.1 and S9.6 all specify
   "load v1, save v2, reload, prove idempotence" against a document format that never existed.
   Those migration gates were unarmable. A persistence story (**S0.1**) is now a prerequisite of
   S2.2 — user decision, taken.
2. **WebGPU works here, but the house test profile hides it.** Measured over `http://localhost`:
   real Intel Xe-LPG adapter, device acquired, `maxTextureDimension2D = 16384`,
   `maxStorageBufferBindingSize = 2 GiB`. Under the suite's SwiftShader flags `requestAdapter()`
   returns **null**, and `navigator.gpu` is undefined on `file://` outright. 77 of 78 oracles use
   those flags. Every Sprint 10 GPU gate written to the house pattern would have been vacuous.
3. **Five oracles could not load at all under Node 25** — ESM-shaped `.js` files under a
   `"type": "commonjs"` directory. Two of them, `_verify_landforms.js` and `_verify_surface.js`,
   are the gates for S1.1 and S1.2, the stories recorded as DONE. The **74/74 green record below
   is stale** and is being replaced by a fresh measured sweep.

### What landed

| Commit | What |
|---|---|
| `35200f6`, `25974a2` | MC-S04 recovered by cherry-pick — S1.3 tone/morphology filters, S1.4 coordinate filters, S1.5 Aspect. 11 node types, 3 oracles. One mechanical `_digest_baseline.json` conflict (HEAD had re-baselined `volcano`; the branch inserted `transpose` adjacent) resolved keeping HEAD's numbers. |
| `7a0fbb7` | The five unloadable oracles converted to CommonJS. |
| `28a4f5f` | S1.0's armed control was `({...TYPES.fracture, cat:'ero'}).cat !== 'surface'` — a literal compared to a literal, constant true on every possible build, ANDed into `ok` as if it were a gate. Replaced with `--mutate=fracture-under-erosion`, which reclassifies the live registry: green `toolbox=Surface / Geology`, red `toolbox=Erosion`. |
| `7a79340`…`9fd22ea` | MC-S33 isolated verification runner adopted **on measured evidence** — OS-selected ports, private profile/TEMP, owned-process cleanup, dist-only build cache, fail-closed sweep preconditions. 33/33 self-tests. |
| `716a978` | WebGPU launch profile (`tests/legacy/_gpu_launch.cjs`) and `_verify_webgpu_capability.js`. Also corrected the export button's false "16-bit PNG" claim — `exportHeightmap` writes `*255` through canvas `toDataURL` and cannot do otherwise. |

### Gate readings

    npm run plugins:check                       79 modules, clean
    npm run verify -- _verify_digest.js         PASS 79/79 bit-identical, skipped 0
    npm run bridge:check                        PASS 207 symbols, unknown 0, no drift
    node --test tests/runner/…runner.test.mjs   33/33 pass
    _verify_filters_pack.js                     exit 0, 41 assertions / 19243 samples
    _verify_coordinate_filters.js               exit 0, 30 assertions / 262176 samples
    _verify_aspect.js                           exit 0, 9465 compared, maxError 1.18e-7 < 1.87e-3
    _verify_landforms.js / _verify_surface.js   exit 0 (had been unable to load at all)
    _verify_webgpu_capability.js                PASS, adapter+device, 12 assertions, 0 failed
    mutation controls                           RED 11/11 (S1.3–S1.5) + 1/1 (S1.0) + 2/2 (WebGPU)

### Wave gate — the real number

    node scripts/sweep-oracles.mjs
    SWEEP discovered=81 declared=81 started=81 completed=81 skipped=0
    81/81 green

**This replaces the stale "74/74 green" record above**, which was not merely out of date but
unreachable: five oracles could not load, so the suite had been reporting on 76 of 81 files.

The first run of this gate was 80/81, and the failure was a regression the focused gates could not
see. Recovering MC-S04 brought a preview-adapter hook, and `bakeThumb` read
`TYPES[nd.type].previewAdapter`, which throws on an unregistered type. `_verify_hex_sampling` S5
died before measuring anything and reported `undefined/undefined`. Fixed at all three call sites
(`1b2696c`); S5 now reads `0/48` duplicate bottom rows where it predicted 6, square control also
`0/48`.

Sprint 1 is complete on evidence: S1.0–S1.5 all have armed red and green endpoints.

### In flight — S0.1 and S2.1 foundations

Three pure, DOM-free modules are committed and **not yet imported**, so the app and the digest are
untouched:

- `src/core/project.js` (`0b55efe`) — the versioned project document. Normal form makes
  save→load→save byte-identical; values are written verbatim and the cases JSON would silently
  corrupt are refused (non-finite numbers, TypedArrays, undefined/function/symbol).
  `migrateProject` is a version dispatch with an injectable table, so S2.2 adds one line.
- `src/core/ports.js` (`298261d`) — ADR-002 vocabulary and `canConnect`. Three rules corrected
  against measured behaviour: mask inputs are generic (declaring `semantic:'mask'` would make ~30
  shipped wirings illegal), unit compatibility is identity not dimensional equality (the ADR
  contradicts itself; identity is the only reading under which `rad→deg` is refused), and a
  `semanticFrom` source is deferred at connect time rather than resolved.
- `src/core/legacy-ports.js` (`13508b9`) — the frozen 79-row table. Port ids seeded once from
  measured `def.ins` labels and never recomputed. 0 validation problems; a generator output
  reaches all 30 mask slots with 0 refusals.

### S0.1 and the S2 keystone — shipped

| Story | What landed | Gate |
|---|---|---|
| **S0.1** | Save/Open project, `Ctrl+S`/`Ctrl+O`, versioned document, `migrate()` dispatch, `_demSrc` source capture | `_verify_project_io.js` armed **13/13** |
| **S2.1** | Typed port descriptors, frozen 79-row legacy table, adapter at registration | `_verify_port_contract.js` armed **8/8** |
| **S2.2** | Schema v2 `{from,fromPort,to,toPort}`, v1→v2 migration, multi-output graph UI | same, plus v1 migration gates |
| **S2.3** | Typed result contract across all three evaluators, per-output cache, demand-driven allocation | `undemandedOutputNotComputed` |
| **S2.6** | **Normals** — vectorRaster, two outputs, the first real multi-output node | digest `port_normal` |

Digest: **80/80 bit-identical, skipped 0**. The re-baseline for `normals` was scoped and proven so —
`nodeCount 79→80`, one entry added, **zero existing entries changed**.

### Defects these gates caught that inspection did not

1. **The graph sink lost its value.** `output` (`cat:"out"`) publishes no port — no outgoing wire —
   but its `eval` returns the terrain the renderer, exporter and `collectScene` read through
   `_field`. Typing the runtime made zero-declared-outputs mean zero value, and `outputNode()._field`
   went `undefined`. **The digest stayed green at 79/79 throughout**, and could not have done
   otherwise: it calls `def.eval` directly and never evaluates through a sink. Three product oracles
   going red together caught it; stashing the change and watching them recover proved it was mine.
2. **The reader accepted a v2 edge with `fromPort` missing.** The writer refuses to emit one, but
   validation skipped the source check when the field was absent — so a truncated file would
   validate and then resolve positionally, the exact fragility v2 removes.
3. **`validateProject` still checked `edge.slot`**, which a v2 edge does not carry, so every v2 load
   failed `EDGE_SLOT_RANGE`.
4. **Three mutations were vacuous on first write** and were repaired rather than counted:
   `round-curve` rounded "4+ decimals" when the default skirt has 1–2; `uid-from-count` set a uid
   that still exceeded every id; `mask-strict-semantic` checked template graphs, which wire **no
   mask slots at all** (24 shipped edges, not one a mask).

### Corrections to ADR-002, forced by measurement

- **Mask inputs are generic (`anyMask`), not `semantic:'mask'`.** Declaring them strictly would make
  all 30 mask wirings illegal — `_verify_digest` drives a plain perlin into every one.
- **Unit compatibility is identity, not dimensional equality.** The ADR says both; identity is the
  only reading under which `rad→deg` and `degC→K` are refused.
- **A `semanticFrom` source is deferred at connect time**, not resolved — 20 of 80 types have one.

### Sprint 8 (first half) and Sprint 9 (opening)

| Story | What landed | Gate |
|---|---|---|
| **S8.1** | Route (typed identity) + Edge (mask boundary, 4-neighbour square / 6-neighbour hex) | armed 4/4 |
| **S8.2** | Switch / Gate — unselected branches never evaluated, via `demandInputs` | armed 4/4 |
| **S8.3** | Typed variables + lexical scope chain; rename-safe by stable id | armed 5/5 |
| **S8.4** | Safe Math — parsed AST, allowlist, bounded size/depth, no `eval` | armed 5/5 |
| **S9.1** | `WorldDomain/1` — independent axes, honest spacing, datum+range vertical frame | armed 5/5 |
| **S9.2** | New Terrain dialog + allocation-free feasibility preflight | armed 5/5 |

Node types **79 → 86**. Document schema at **v3** with a working two-step migration chain
(v1→v2 port identity, v2→v3 world domain). Wave sweep after the keystone: **83/83 green**.

`scripts/gate.py` now runs a story's whole evidence set in one command — the oracle green plus
every declared mutation — and fails on both `NOT ARMED` (mutated run exited 0) and `VACUOUS`
(only the safety net tripped).

### More defects the gates caught

5. **`constructor` escaped the Safe Math allowlist.** `'constructor' in EXPR_CONSTANTS` is `true` —
   `in` walks the prototype chain — so it parsed as a literal whose value was the `Object`
   constructor. Same for `toString`, `__proto__`, and the function table. Lookup tables are now
   null-prototype with `Object.hasOwn`. Found only because the oracle attempts the escapes
   explicitly and demands a *named* refusal; testing arithmetic would never have surfaced it.
6. **The Switch fixtures evaluated through the Output sink**, which normalises its input and
   rewrote the very constants used to identify a branch — three gates red for one cause.
7. **`_verify_menubar` broke twice on S9.2** and was right both times: a stale `page.once('dialog')`
   for a `confirm()` that no longer fires, and a blank-state expectation describing the old
   immediate-wipe. The replacement is stronger — cancelling the dialog must leave the document
   untouched.

Page arithmetic for arbitrary dimensions was derived independently and matches ADR-009 exactly:
`16384²` → 64×64 pages, terminal core 255×255; `1573×13789` → 7×54 pages, terminal core 36×220.

### The Sprint 1+2 audit, and what it cost to answer

An adversarial audit returned **8/8 UNSUPPORTED with 124 gaps**. Most of it was real. Verified and
fixed, in the order found:

1. **`_verify_port_contract.js` was red in the tree.** S8.1's Edge node has a Mask input, taking
   `maskSlots` from 30 to 31 against a pinned literal. I ran `--core` after that story but not the
   affected oracle, so I shipped a red gate and reported it green. The pin is gone: the gate now
   asserts every `role:'mask'` port also declares `semantic:'anyMask'` and accepts a dimensionless
   generator, which cannot go stale on a new masked node.
2. **`gate.py` parsed zero mutations for 7 of 17 oracles** — the regex required the closing bracket
   at line start. Controls visible to the runner: **57 → 107**.
3. **`_verify_landforms` and `_verify_surface` were failing unmutated** on
   `"WebSocket closed without opened."` — Vite's dev client with no socket to attach to in
   middleware mode. I had documented this exact hazard when building the WebGPU probe and then
   filtered it in that one oracle instead of fixing the source. It is timing-dependent, so the
   83/83 sweep reported earlier was **luck**. Fixed at the runner (`/@vite/client` served as a
   no-op); all ten per-oracle suppressions removed.
4. **`mutationReached` was computed, printed and never asserted**, with `ok` forced false under any
   mutation — so every mutated run exited 1 whether or not the mutation broke anything, and none of
   Sprint 1's 37 controls had ever been *shown* to detect what it claims. Running them properly for
   the first time: **17/17 landforms, 20/20 surface**.
5. **`worldMapping` was an Array carrying an `.ok` property** — non-index properties do not survive
   `page.evaluate` serialisation, so it was `true` in the page and `undefined` in Node.
6. **Four visual controls were dead** in every automated run (only checked inside `--visual`, which
   the sweep never passes), and `visual: {runs: [], ok: true}` passed on an empty capture set.
7. **Constant-true controls replaced**: landforms compared two hard-coded literal arrays; S1.5's
   only control computed its circular mean from test-side literals. Both now measure production —
   and the replacements are themselves proven falsifiable.
8. **Two fixtures were red for the wrong reason**: `raw-odd-r-transpose` reversed an array instead
   of transposing (now fails on **hex only**, which is the point), and `match-cdf` substituted a
   scaled source instead of a histogram match.
9. **A wall-clock gate failed on contention** — canyon `buildMs` 4447 in-sweep vs 1742/1797/1736
   standalone. Fixed by measuring best-of-three, **bound unchanged at 3000**.

**One audit finding did not reproduce.** It claimed the spectral scale-invariance gate "passes on
the broken build" with `wavelengthDelta` exactly 0. Measured: 1737.66 against a 39.06 bound — the
gate catches it. Recorded rather than dropped, because how much of the remaining findings to act on
depends on the audit's hit rate.

### Sprint 8 — complete

| Story | What landed |
|---|---|
| S8.1 | Route (typed identity) + Edge (4-neighbour square / 6-neighbour hex boundary) |
| S8.2 | Switch / Gate — unselected branches never evaluated, via `demandInputs` |
| S8.3 | Typed variables + lexical scope chain, rename-safe by stable id |
| S8.4 | Safe Math — parsed AST, allowlist, bounded size/depth, no `eval` |
| S8.5/S8.6 | Versioned subgraphs — content identity, recursion refused at registration, instance cache |

Node types **79 → 87**. Digest **87/87, skipped 0**. Eleven oracles armed, **zero vacuous**.

More defects the gates caught in new work: `constructor` escaping the Safe Math allowlist via the
prototype chain; the graph sink losing its terrain while the digest stayed green; a v2 edge accepted
without source identity; `definitionHash` changing on every save/load because it was key-order
dependent.

**Next:** Sprint 8 post-sprint audit, then S9.3, then the physical stack S3 → S4 → S5.

---

**DIRECT FIX PASS — 2026-08-03, commit `36d37b2`.** User-reported visual bugs and two follow-on
feature requests landed and were verified directly against the running dev server (no Mission
Control lifecycle — routine, single-owner, low-risk work per `DELIVERY.md`):

- Volcano centre spike fixed: `(1-rn)^2.2` had nonzero slope at the vent, a literal cone apex.
  Hermite-capped below `rn=0.12` to zero slope at centre. Verified against
  `_verify_landforms.js` (full pass) and the digest oracle (only `volcano` changed, re-baselined).
- Canyon edge/border weathering fixed: `canyonSurfaceExpression` skipped the outermost 1px ring,
  leaving an unweathered seam at every domain edge. Extended to the full field with boundary-safe
  one-sided differences. Verified against the full 11-test `_verify_all_canyon.js` suite and the
  digest oracle (only `canyon` changed, re-baselined).
- Volcano **Age / weathering** param added (default `0`, bit-identical to prior output — zero
  digest drift at default). Nonzero age warps the footprint, degrades/breaches the rim, and adds a
  hummocky crater floor. Smoke-tested via Playwright: age 0 vs 0.7 differs on ~79% of pixels, no
  NaNs, sane bounds.
- Canyon **trunk waypoints** added: optional `x,y`-per-line text param (default empty, bit-identical)
  plus a graphical top-down click/drag plan-view editor (mirrors the existing Draw Mask editor;
  button reads "Edit waypoints on terrain…" in the Canyon node's params panel). Verified the compute
  path (waypoints correctly relocate the trunk, confirmed via column-mean argmin) and the UI path
  end-to-end with real Playwright clicks/drags (add/drag/undo/clear all confirmed via DOM state).
- All four changes: full oracle suites green, 68/68 digest bit-identical, clean production build.

Still open from the same conversation, not started: **mountain ranges via waypoints** are already
covered by the existing Layout node (`path` shapes with per-vertex elevation) — no new code needed,
just point users at it. The larger backlog items below (Boundary Landforms, arbitrary dimensions,
GPU-only mode, Walkaround) remain untouched.

---

### Sprint 8 — the post-sprint audit, and what it cost

The audit rated **6 of 6 stories UNSUPPORTED** with 91 gaps, against six oracles that were all green.
It was right on every count, and the work it forced is the seventh instance of this project's
standing failure mode. The pattern is written up in `BACKLOG.md` §5; the position is here.

**Eleven controls across four files assigned the answer instead of breaking production.** They went
red when mutated, so `gate.py` called them armed, and they proved only that a test can edit a local
variable. All eleven are rewritten to perturb an input production consumes.

What the repair uncovered, none of it visible to the gates that existed:

| | Defect | Evidence |
|---|---|---|
| S8.2/S8.5 | **The editor never type-checked a wire.** `canConnect` had existed since S2.1; `grep -nE "canConnect" src/legacy.js` returned two lines — the import and the bridge re-export. | `7036e12` |
| S8.6 | **Two instances served each other's terrain.** Cache identity keyed upstream on `String(ins[0].length)`; every field is RES², so the term never discriminated. Instance A fed by perlin and instance D fed by ridged returned the *identical Float32Array*. | `ec87490` |
| S8.6 | A nested definition's hash was not part of its parent's identity, so a dropped inner definition still served a cached result computed from it. | `ec87490` |
| S8.5 | **Nothing pinned anything.** ADR-004 requires `(definitionId, version, fullHash)` and "old instances never float"; registering v2 replaced v1 in place and moved every existing instance's output. | `1e073ea` |
| S8.6 | An embedded definition's stated hash was never verified on load — a document claiming `deadbeefdeadbeef` loaded silently. | `1e073ea` |
| S8.4 | **Unit validation was entirely absent**: `grep -nE "unit" src/core/expr.js` returned zero matches. | `c87c333` |
| S8.3 | Variable output hard-coded `unit:'none'`; `graphSnapshot()` omitted variables, so a variable edit wrote **zero** undo records; subgraph overrides were merged into node params while the header comment claimed a scope frame that had one caller and one frame. | `cbbce15` |
| S8.1 | **Chokepoint had never been built** — one comment matched it in the whole tree. And Route declared `kind:'scalarRaster'`, so the registry's only vectorRaster could not enter the identity node the story requires to carry it. | `e0dac3a` |

Two mechanical traps, both of which report as success, are recorded in `BACKLOG.md`: a mutation of a
frozen object is a silent no-op under sloppy-mode `page.evaluate`, and a positional signature called
with an options object made three "templates" measure the same graph three times.

Controls now armed on these six stories: **flow control 5, connect-time 3, variables 8, math 11,
subgraph 7, subgraph persistence 18** — every one seen red, zero vacuous.

### Sprint 3 — the cover layer, red-first throughout

Sprint 3's Ready condition requires its acceptance fixtures **observed red before the implementation
exists**. Four were written that way, each failing by named gates rather than throwing, and each
registered in `tests/legacy/expected-red.json` so the sweep prints them every run and fails if one
turns green without the register being pruned.

| Story | State | Gate |
|---|---|---|
| S3.1 hydraulic state outputs | **done** `bfe18e8` | sediment state 6/6 armed, 30 gates |
| S3.2 regolith producer | **done** `e3114c4` | soildepth 4/4 armed, 22 gates — **now red, see below** |
| S3.3 cover-aware transport | **done** | cover erosion 8/8 armed, 36 gates, register pruned |
| S3.4 explicit state selectors | **done** `c468185` | cover reader 8/8 armed |
| S3.5 transport co-evolution | **done** — ledger 4 → 0 | transport co-evolution 8/8 armed |

### S3.5 — the exemption ledger reached zero

Four commits, one node each (D21), each with a digest delta naming that node and nothing else. **Not
one of the four needed a re-bless**: the cover work is demand-gated, so a graph that wires no cover
publishes the field it published yesterday, byte for byte, and `_verify_digest.js` — which evaluates
with no `ctx` at all — never sees the typed return.

    transport=4 compliant=4 ledger=0 coUpdateTargets=2 deliveryRows=4 undelivered=[]
    npm run verify -- _verify_digest.js     92/92 bit-identical, skipped 0

`hydraulic` was last. Its implementation was S3.3's and is untouched; only the ledger reading was
outstanding. Three things had to be settled to flip it honestly.

**`wetness` was dropped, on measurement rather than convenience.** The pipe solver does carry a
per-cell water column that S3.1's atlas already reads back, so publishing it would have cost no
second synchronisation point — the question was whether it is a wetness map. It is not, on five
independent readings plus the doctrine:

| Reading | Measured |
|---|---|
| Magnitude is the iteration slider | mean 0.00888 (8 iters) → 0.07870 (360), tracking the no-flow `(w+rain)·evap` recursion to within 1%; **51.3% converged** at the shipped 48 |
| Pattern is not stable either | Pearson r vs the 48-iteration field: 0.493 / 0.762 / 1.000 / 0.686 / 0.418 / **0.176** |
| Not Res-Lock invariant | gridK 1/2/3 → means 0.0404 / 0.0393 / 0.0373, correlations 1.000 / 0.433 / 0.316 |
| It is a depth, not an index | normalised height units × relief = metres; that is `waterDepth` (S4.4), and normalising it needs a reference nobody has measured |
| One engine of three | GPU droplets return no water key; the CPU droplet ledger has none; hex has no pipe solver |

And sprint-02:194 / `BACKLOG §2` require `wetness` **split, not averaged** — the state map is
path-dependent *saturation*, and "a plugin declaring one does not satisfy the other". Nothing carries
wetness into this node or out of it, so there is no history for a co-update to preserve. The producer
the plan names is S5.3/S5.4; `aux-maps.js` now says so instead of naming S3.3, which shipped without
it. `coUpdateTargets` fell 3 → 2 and the `evidenceNonEmpty` bounds were **re-measured, not relaxed**:
signatures 5 → 4, transport co-update sets 2 → 1, targets 3 → 2, all now exact equalities at the only
values the manifest can produce, with the target names asserted rather than just the count.

**`transport-claims-compliant` was retired, not repointed.** With no exempt row left it could only
assign a value production already holds. What replaces it is the opposite direction taken twice —
`transport-drops-compliance` on the first row S3.5 flipped and the new `hydraulic-drops-compliance`
on the last. Both make `exemptionLedger` emit a real entry again, which is what keeps
`ledger.length === 0` from being an assertion about a function that can no longer produce entries.

**And extending `_verify_cover_erosion.js` found three half-gates in it — including the one this
sprint has now hit four times.**

1. **The cover-book bound scaled with standing cover, not with what moved.** On the shipping square
   GPU path the shipped bound sat **2.26×** under the transport it constrains, so the closure could
   not have seen 40% of the book go missing. Corrected to the double unit over the absolute per-cell
   *change*: arming 4.8e11 … 2.2e12. Both endpoints are re-measured every run, so the rejected bound
   is a live delta rather than a note.
2. **The ledger bound had no arming at all.** Measured 4.2× on the pipe path, 282–340× on the droplet
   paths — tight, armed, and now asserted. Its float32 unit is kept deliberately: the loss side is
   the solver's own float32 accumulation and the residual is the kernel's real non-conservation.
3. **The refusal had never been exercised.** `resolveCoverLoss` publishes nothing for `gpu-droplets`
   and `gpu-combined`, whose export is `sumIn - sumOut` — but every run was pipe-only, so no run ever
   reached either engine under cover demand. That refusal was a claim in the manifest with no gate
   behind it. Two runs now reach them and it is graded on four readings, including *which engine
   actually ran*, so a silent fallback to the CPU droplet kernel cannot pass as a refusal.

Armed controls: cover erosion **8/8**, transport co-evolution **8/8**, zero vacuous.

### Defect found, NOT fixed here: `_verify_soildepth.js` is red in the tree

Measured red **before and after** this change, identically — `git stash` on the unmodified tree
reproduces the same 14 failed gates. It is S3.2's gate and the cause is S3.5's own work:

    FAIL soildepth producer=erosion2 ... failed=[producerRegistered, ...14]

Discovery is by output semantic `soilDepth`, discriminated by "a producer integrates over time" — a
param matching `/duration/i`. That discriminator was itself the repair for an earlier collapse of the
same kind. It has now collapsed again: `erosion2` gained a `soilDepth` output in S3.5c **and** has a
`duration` slider, so it satisfies both tests and sorts first. The gate is behaving correctly; the
discriminator needs a third form (the Heimsath `p0`/`hStar` params are the obvious candidate, being
the thing only the producer can have). Left alone deliberately — it is outside this commit's files
and fixing it here would confound the one-node-per-commit delta.

Node types **88 → 92**. Preconditions that had to be built first because the sprint assumed them:
the port vocabulary (`soilDepth`, `sedimentDepth`, `sandDepth`, `solidTop`, `bedrockHeight`,
`precipitation`, `mmPerYr`, `yr`), the two-frame height adapter (**D20**), and the transport-class
manifest — because S3.5's acceptance says "the exemption ledger contains no material-transport
entry" and *that ledger had never been built*, so the clause passed vacuously over a structure that
did not exist.

**The measurement that mattered most.** The hydraulic mass ledger closed by construction: every loss
term was a difference of sums over *nested* cell sets, so the identity held for any implementation
including one that deletes the terrain — and the guard meant to catch exactly that, `exportedDerived`,
was a hardcoded `false` on the same object. The apron ring is now accumulated over a cell set
**disjoint** from the core:

    cropExchange     3.632687   core loss
    exportedToApron  3.632644   apron gain, independent
    agreement        1.2e-5 relative

S3.1's armed closure goes further: it recomputes the field side in the oracle and takes the loss side
from production's accumulators, so a `height-deleted` mutation leaves a residual of **99.9% of the
budget** against a bound 1000× smaller. It cannot pass for an implementation that deletes the terrain.

**Three half-gates found, all by running things rather than reading them.** Port descriptors
snapshotted *before* a mutation block, so the assertion read pre-mutation values and could never
fail. Discovery by output semantic that broke the moment a second node legitimately published the
same semantic — a producer *integrates over time*, a selector reads a wire, so the duration parameter
is the discriminator. And a descriptor-only check that would have passed on a port declared but never
filled.

**And one in the instrument itself.** `gate.py` scored a mutation ARMED whenever the mutated run
exited non-zero, never comparing against the unmutated run — so a red-first oracle armed every
control it declared while arming nothing. Measured on the first four: 4 of 5 false. Arming is now a
**delta**.

**DELIVERY RECOVERY — risk-based fast path adopted, 2026-08-02.**

Canonical execution policy: [docs/plan/DELIVERY.md](docs/plan/DELIVERY.md). Quality is unchanged,
but focused evidence now runs per changed slice and exhaustive evidence once per integrated wave.
Routine one-owner work no longer pays the full Mission Control lifecycle; high-risk contracts,
migrations, runtime work, and real lease contention still do.

### Visible delivery checklist

- [ ] Diagnose and green the MC-S33 runner contract
- [ ] Review, integrate, and publish MC-S33
- [ ] Replay S1.3–S1.5 on the published runner and close Sprint 1
- [ ] Publish the S2 typed-port keystone
- [ ] Start the first four disjoint Wave 2 lanes
- [ ] Integrate the S3–S5 physical stack
- [ ] Complete S6/S8/S9 integration
- [ ] Calibrate S10.R0 and deliver S10
- [ ] Pass exact `16384 x 16384` and `1573 x 13789` GPU-only terrain gates
- [ ] Deliver Boundary Landforms and doll-based Walkaround/reachability with no flight
- [ ] Pass final built digest, standalone sweep, applicable e2e/PWA, and audit

- Canonical runtime: `C:\repos\GitHub\skills\.mission-control-plan`, driven only by the installed
  skill at `C:\Users\AlexanderPino\.agents\skills\mission-control`. The repository's
  `mission-control/` skill is not part of this programme and must remain untouched.
- Integration product baseline is `97d163f`. Sprint 1 stories S1.0, S1.1, and S1.2 are **DONE**;
  shield and stratovolcano modes shipped through MC-S32. MC-S30/31/32 are canonical `done` items.
- `MC-S04` (S1.3–S1.5 filters, coordinate transforms, Aspect) is committed at `3ebcb8d` and all
  product/focused/source/built/digest gates are green at 79/79 with zero skips. Canonical verdict is
  `oracle-broken`, not product-red: Node 25 CommonJS handling and the fixed/reused 5173 launcher make
  the exact bridge/blur/sweep commands unable to grade the item honestly. Its 19 leases remain held.
- `MC-S33` is the quality-preserving throughput fix for that infrastructure: isolated OS-selected
  ports, private browser profiles/TEMP, owned-process cleanup, byte-preserving CommonJS execution,
  one server per mode, and verified `dist/`-only build cache. It is `building` with seven leases.
  Its worktree currently has modified `package.json`, `run-legacy-verify.mjs`, and
  `sweep-oracles.mjs`; new runner/cache/bootstrap/test files; and an untracked `runner-focused.log`.
  There is no `handoff.md` and no commit yet. The last `npm run verify:all` exited 1 and must be
  diagnosed from output before any claim of completion; do not widen/skip oracle evidence.
- After MC-S33 publishes, create the reviewed retry item proposed as `MC-S45` with
  `origin: split:MC-S04`, dependency `MC-S33`, and the same canonical S1.3–S1.5 scope. Replay the
  MC-S04 commits onto the published runner base and verify through the new exact commands. Do not
  mutate or relabel MC-S04 history.
- Approved and waiting behind shared central-file leases: `MC-S01` (typed document/ports),
  `MC-S21` (large-world domain/dialog/import metadata), and `MC-S25` (graphics capability modal).
  Open dependency queue begins with MC-S02/S05/S06/S07/S12. Sprint 9 and cook-free Sprint 10 are in
  the canonical roadmap; Sprint 10 remains refinement/Ready-blocked until its S10.R0 calibration.
- Measured bottleneck: repeated verification infrastructure failures and `legacy.js` lease
  serialization, not feature coding. Publish MC-S33 first. Add a digest-preserving extraction only
  when two ready bundles demonstrably contend on the same file; scaffolding is no longer a separate
  programme. Acceptance semantics, armed controls, built checks, and the integration-wave sweep
  remain mandatory.

Continuation prompt: [CONTINUATION.md](CONTINUATION.md).

**Arbitrary dimensions, GPU-only high-resolution authoring, Boundary Landforms, and Walkaround —
accepted into the roadmap, implementation NOT STARTED, 2026-08-02.**

- ADR 009 requires exact independent sample dimensions with no power-of-two rounding. Named gates
  include `16384 x 16384` and `1573 x 13789`; 256-cell page controls produce `64 x 64` pages with
  255 valid terminal cells and `7 x 54` pages with a `36 x 220` terminal core respectively.
- High-resolution `gpu-required-paged` mode forbids CPU terrain-field computation, whole-raster CPU
  arrays, full-field readback, and silent fallback. CPU remains a bounded metadata/IO/control plane;
  every demanded terrain node must have a validated paged WebGPU implementation or preflight rejects.
- Sprint 7 adds S7.6 Boundary Landforms: selected north/east/south/west hills, asymmetric mountain
  chains, and heightfield cliffs with metre-authored profiles, arbitrary dimensions, and a GPU path.
- ADR 010 and S10.9 add a Street-View-style doll placement tool, fixed-step Rapier WASM capsule
  controller, walk/run/jump, collision-first streaming, WebGPU reachability overlays, and route
  replay. There is explicitly no flight, noclip, ascend, or descend action.
- Sprint totals are now S7 36, S9 66, and S10 81. The ten-sprint programme is **417 points**. Future
  traceability bundles are MC-S37 Boundary Landforms, MC-S38 arbitrary dimensions, MC-S39 GPU-only
  graph evaluation, and MC-S40 Walkaround/reachability; no canonical runtime item was created by
  this planning change.

**Sprint 10 cook-free runtime heightfield / Extreme Detail — canonical plan grounded, technical
refinement/Ready BLOCKED on S10.R0 calibration, implementation NOT STARTED, 2026-08-01.**

- Added the original 60-point Sprint 10 packet and accepted ADR 008; ADRs 009/010 later expand
  Sprint 10 to 81 points and the programme to **417 points**. `ExtremeCapability/1` requires secure context, `navigator.gpu`, a
  non-null adapter/device, no optional features, WebGPU guaranteed-default minimum limits, and
  validated core format usages. Standard requires WebGL2 plus `EXT_color_buffer_float`.
- Capability wording is **“No supported graphics capability,”** not “no GPU.” Browser APIs do not
  reliably prove physical GPU versus SwiftShader/software or report VRAM. Headless SwiftShader is a
  valid endpoint when requirements pass. Persisted preference cannot bypass a fresh probe;
  insecure-context/API-absent/adapter-null/device-reject/device-lost diagnostics remain distinct,
  while timestamp queries are diagnostics only.
- Extreme pages have profile-authored power-of-two core cells, `coreCells+1` posts, `coreCells`
  shared-edge stride, declared aprons, explicit parent/downsample registration, and persisted
  conservative min/max/error headers. Local edits create a `surfaceVersion` and invalidate leaves,
  apron dependants, ancestors, and caches; domain/GLOBAL edits invalidate broadly. S10.2 owns pinned
  roots, ancestor fallback, cancellation, old-front retention, and atomic promotion.
- Geometry is pure fixed-topology clipmap rings. Error metadata prioritizes residency/quality labels
  only. Overlapping toroidal motion uploads exposed strips; a teleport beyond the logical span uses
  budgeted multi-frame full logical refill while an ancestor renders. CPU texture scrolling and
  unbudgeted same-frame refill are forbidden.
- WebGPU compacts visible records into one instance buffer and issues exactly one `drawIndexedIndirect` per
  fixed pass/material/index-pattern bucket with `instanceCount=visible patches` and
  `firstInstance=0`. Shader `instance_index` addresses compacted records; CPU encoding is O(fixed
  buckets), and `indirect-first-instance` is not required.
- S10.5 owns scaled asynchronous feedback, real eviction, the complete byte plateau, and analytic
  camera-relative precision `<=1 mm` at 100 km. Platform frame/memory budgets are authored inputs.
  Software depth/patch-ID controls are byte-identical; GPU parity uses a one-ULP mismatch formula.
  Visual displacement is identical in main/depth/shadow/velocity, and dependent surface consumers
  declare authoritative-height or visual-displacement use.
- Anti-tiling still lacks measured periodic/decorrelated autocorrelation controls. The zero-point
  S10.R0 readiness-only story must freeze that bound and the GPU parity bound between measured red/green
  controls; until then Sprint 10 is not technically refined or Ready.
- Mission traceability adds future roadmap bundles `MC-S25`–`MC-S28`; `MC-S20` must eventually wait
  for `MC-S28`. No Mission Control SQLite/runtime item or dependency was created by this documentation
  change. Export waits for the Sprint 6 and Sprint 9 manifest owners and remains height, auxiliary,
  and domain/region pages only; runtime caches regenerate after import.

**Sprint 9 large worlds — canonical plan grounded/refined, implementation NOT STARTED, 2026-08-01.**

- Added the original 61-point large-world packet and accepted ADR 007; ADR 009 later expands it to
  66 points with exact arbitrary sample dimensions. The base contract includes versioned independent-width/height
  world domains, m/km/mi/ft input with internal metres, vertex/legacy posting, vertical datum/range,
  allocation-free New Terrain preflight, and import metadata with explicit embedded/inferred/override
  provenance. Sprint 9 brought the then-current programme to **326 points** (`265 + 61`); Sprint 10
  is followed by the Sprint 10 total recorded above.
- The selected architecture is one authored/derived full-domain substrate for GLOBAL nodes plus
  deterministic LOCAL/NEIGHBOURHOOD evaluation regions with transitive support-radius aprons. Global
  results are sampled into regions; cosmetic seam crossfade is not correctness. Preview keeps a
  byte-bounded active hierarchy with cancellation, eviction, and camera-relative rendering rather
  than materializing a 40-billion-sample graph.
- Canonical arithmetic is fixed: 100 km at 0.5 m `cellSizeM` is `200001` square vertex samples per axis,
  approximately 40.0 B samples / 160.0 GB for one R32F field; equal-cell hex is approximately
  46.2 B / 184.8 GB. An illustrative 5 km evaluation partition is `100/5=20` per axis and **400
  regions** total; actual evaluation regions and streaming chunks are much smaller and budget-derived.
- Mission Control traceability extends to `MC-S21`–`MC-S24`. These are future implementation
  bundles in the roadmap only; no Mission Control runtime item/state was created or changed.
  Domain/dialog/import may start early; tiled evaluation waits on `MC-S02`, manifest integration on
  `MC-S14`, and reusable-definition constraints on `MC-S19`.
- The plan names a user-selected 100 km-class target and makes no unsourced claim about the actual
  dimensions of *Star Wars Outlaws*. GeoTIFF decoding remains a separate future codec/library story.

**Sprint 1 implementation — S1.0, S1.1 and S1.2 DONE (`da2e583`, `8a83bcf`, `c096ed1`), 2026-08-01.**

- Added the ninth palette family and reclassified Rock Fracture from Erosion; Thermal remains
  Erosion. Toolbox search and drag-out quick-create expose the new family without evaluator changes.
- Focused Surface-family oracle, toolbox, quick-create, 61/61 digest, plugin/bridge checks, and
  production build are green. The broader sprint-grounding ledger remains open; only grounded,
  independently gated stories may enter implementation.
- MC-S31 integrated Surface Detail plus the initial landform pack with seed lifecycle, direct/CJS
  68/68 digest, 32 armed mutations, full source/built 45° visual matrices, FOV state preservation,
  plugin/bridge/exact/hex/build gates, and clean independent review. This closes **S1.1 only**.
- MC-S32 completed the S1.2 Volcano correction: shield uses the grounded broad 2–10° dome family;
  stratovolcano uses the 20–35° summit-steepening profile with crater and barrancos. Distinct direct
  square/hex formulas, slope bands, style persistence, 17 armed mutations, 16 source/built 45°
  captures, repeat 68/68 digests, plugin/bridge/build gates, and independent review are green.

**Sprint 4 scope expanded — AAA hybrid Gerstner water accepted locally, 2026-07-31.**

- ADR 006 keeps hydrology still and renderer motion separate, then adds shared displaced Gerstner
  geometry, analytic normals, GGX/Fresnel/Beer-Lambert optics, flow-driven rivers, causal foam,
  shore/ice regimes, supplied-reference captures, pass parity, temporal and frame-budget gates.
- Sprint 4 now carries S4.7–S4.10 as separately routable renderer stories; no wave or foam data is
  baked into terrain fields or export products.

**Sprints 1–8 — grounding ledger applies per story, 2026-08-02.**

- The first refinement pass added contracts, cut order, verification matrices, and Ready conditions,
  but an audit found that some “locked” defaults and runtime choices had no corpus, measured-code, or
  accepted-ADR evidence. Those claims still require correction before their owning stories start.
- Mission Control investigation `INV-SPRINT-GROUNDING` owns the correction. Completion requires a
  claim-level grounding ledger, accepted ADRs for S2/S6/S8, removal or replacement of unsupported
  mechanics, fixed pre-implementation thresholds, and an independent rubber-duck review with no
  valid blocking finding.
- Readiness is now local: an unresolved claim blocks its owning story and consumers, while unrelated
  grounded stories proceed. Ledger-wide closure remains a final programme gate.

**Separate GPU Rock Fracture node — done locally, 2026-07-31.**

- Added an erosion-family **Rock Fracture** node instead of folding cracks into Thermal. It carves
  deterministic warped Worley/Voronoi `F2−F1` joint boundaries at up to five scales. Fine sets become
  shallower and narrower, avoiding the nearly uniform lowering produced by reusing the broadest
  crack and shoulder at every octave.
- **Fracture network** and **Edge weathering** are independently switchable, collapsible inspector
  panels. Spacing, crack width, cut depth, warp scale, and shoulder width are authored in metres;
  terrain scale/relief edits correctly dirty the node. The intended stack is
  `Rock Fracture → Thermal`: joints first, talus transport second.
- Square terrain runs a one-pass WebGL2 gather kernel with one readback. Hex and systems without
  float render targets use the deterministic CPU compatibility path. Measured square CPU/GPU error:
  max `5.25e-6`, RMS `4.71e-7`.
- The procedural field continues beyond the rectangle rather than sampling a clamped border. The
  focused gate measured edge/interior fracture dose `1.09`, 128²↔256² RMS drift `4.08e-4`, exact
  disabled/masked identity, finite unbounded negative/>1 heights, seed determinism, strict `[0,1]`
  masks, hex fallback, toolbox registration, GPU badges, and collapse-state purity.
- Visual evidence on a deliberately smooth mountain shows connected multiscale rock joints rather
  than thermal ribbing. A heightfield limitation is stated in the inspector: grooves and breakup
  are representable; true separated blocks, undercuts, and open fissure voids are not.

**GPU hydraulic spikes and edge tears — fixed locally, 2026-07-30.**

- Removed the synchronized end-of-lifetime sediment dump that turned every surviving droplet into a
  narrow cone. Lifetime is now a work cap; unresolved load is named `exportedOrSuspended`.
- Fixed the separate high-density runaway. Particle cohorts cap stale-read scatter density at 0.1
  particle/cell; speed is bounded; above 0.5 particle/cell, water/sediment parcel weight shrinks so
  additional particles refine coverage without multiplying strength or breaking the terrain ledger.
  The previous 30k UI / 120k actual case reached finite values around 10²¹.
- Fixed the pipe solver’s self-deepening minima: transport capacity now uses a signed downhill outlet,
  vector speed, and a shallow-water ramp. The post-output fade was removed. Pipe runs on a
  border-continuation apron with an explicit closed outer wall and crops back to the authored field.
  At 279 iterations / Deposit 0.48, edge p99/max are 0.00384/0.00454 versus input
  0.00749/0.00849.
- Droplets spawn inside a full-brush guard and export before reaching a partial edge brush. The
  viewport also keeps the inspection eye above the open heightfield so back-facing mesh triangles
  cannot masquerade as erosion spikes at grazing angles.
- `_verify_hydraulic_dual_gpu` now has armed upward and downward controls and runs the real 512²
  Interactive path: the reported 14,389 × 71 case, 30k, the 60k UI / 240k actual maximum, and exact
  combined Pipe 279 → Droplet 57,670 × 48. All are finite with zero peaks or pits above 0.02. Focused
  verification, the camera-guard rerun, and the current 74/74 standalone-oracle record are green.

**Composable GPU hydraulic erosion — done locally, 2026-07-30.**

- Hydraulic now has independent Pipe / grid and Droplet / particle switches with collapsible,
  model-specific controls. Switches are saved and undoable; expansion state is UI-local.
- Square-lattice WebGL2 runs both mechanisms on the GPU. Pipe state feeds Droplet state in the
  fixed order Pipe → Droplet and the combined node reads back once. The droplet stage uses particle
  textures, MRT updates, additive float point-rasterisation, and a terrain gather/apply pass.
- Old `engine` documents migrate to the two-switch schema. Hex and contexts without
  `EXT_float_blend` retain an explicitly labelled CPU compatibility path.
- `_verify_hydraulic_dual_gpu` gates same-seed repeatability, seed variation, finite output,
  erosion and deposition, mass closure, combined stage order, one readback, inspector UI,
  collapsible-state purity, switch history, and saved-graph migration.

**Graph authoring UX — done locally, 2026-07-30.**

- Releasing an output connection on empty graph space opens a focused, searchable node picker
  containing only node types with an input. Selection creates the node at the release point and
  connects slot 0; create + connect is one undo record, and Escape is a no-op.
- The stacked/vertical workspace has an accessible horizontal splitter. The graph's preferred pixel
  height persists across reloads and display growth. CSS and JavaScript independently preserve a
  220 px terrain viewport by shrinking the graph only when the window is constrained.
- Focused gates green: `_verify_quick_create`, `_verify_workflow`, `_verify_toolbox`,
  `_verify_edges`, `_verify_digest`; production `vite build` green. The subsequent full standalone
  sweep is 72/72 green.

**Programme:** modularisation toward React + plugin nodes + PWA, per
`~/.claude/plans/quiet-wishing-harbor.md` (adversarially reviewed before execution; seven blocking
issues found and folded in).

**Phase B — the original 60 of 60 node types became plugins.** Rock Fracture was then added directly
as plugin 61. legacy.js 7,406 → 6,561 lines during the extraction.

**Phase A — become a module, extract GPU, ship the PWA shell.**

| Step | State | Commit |
|---|---|---|
| A0 · make the four source-text instruments module-aware | **done** | `ca72036` `4d82644` `fe9c8b8` `58659ba` |
| A1 · app becomes an ES module | **done** | `d67e9f8` (blocker `21953aa`) |
| A1b · `--preview` builds with `--mode test` | **done** | `442564a` |
| A2 · extract `src/core/gpu.js` + `gl-util.js` | **done** | `61ca297` |
| A3 · PWA shell | **done** | `ab0a322` |
| A4 · single-file artifact decided (multi-file accepted) | **done** | this commit |

## Gate readings, current

Run from `apps/terrain-studio/`. Everything is HTTP now; `--file` died with A1.

```
npm run verify -- _verify_digest.js     88 node types bit-identical at 256²; skipped 0
npm run verify -- --preview _verify_digest.js   same, against the BUILT bundle
npm run bridge:check                    228 symbols, unbridgeable 0
npm run plugins:check                   88 modules: imports resolve, exports exist, no TDZ
python scripts/gate.py --oracle X       runs green + every declared mutation; flags NOT ARMED
                                        and VACUOUS. An oracle is not done until this is green.
npm run verify -- _verify_blur_isotropy.js   square 1.0000, hex 1.0000 (was 1.185)
npm run verify -- _verify_layers.js     L0 13/13 both lattices; roughness 0.0290/0.0286
npm run verify -- _verify_hillslope_isotropy.js  9/9; hex sigma 3.873/3.873 = square exactly
npm run verify -- _verify_flow_facets.js  12/12; facets 1.0114/1.0220 (single-receiver floor was 1.81/1.67)
node tests/legacy/_verify_shapescan.js  3 files, 8554 lines scanned
npm run verify -- _verify_gpu.js        hasWebGL2Float=true init=true gpuReady=true
                                        fbm@512: 16ms GPU vs 231ms CPU
npm run verify -- _verify_hydraulic_dual_gpu.js
                                        GPU droplets + Pipe→Droplet, one readback, UI/migration green
npm run verify -- _verify_wireframe.js  6/6   (gl.drawElements monkey-patch still takes)
npm run verify -- _verify_hex_deferred.js  4/4
npm run verify -- _verify_erosion_mass.js  9/9
npm run verify -- _verify_glsl_probe.js  maxDiff 0.000e+0 (tol 1e-5)
npm run verify -- --preview-prod _verify_pwa.js   6/6, incl. offline with the network cut
```

Run the app: `.\run-studio.ps1` (dev, :5173) · `-Mode pwa` (build + preview, :4173) · `-Mode build`.

## Shape of the app today

```
index.html          79 KB — markup, <style>, one <script type="module">
src/legacy.js       6,905 lines — the app, + the test bridge spliced in at the end
src/core/gpu.js     GPU, GLSL kernels, gpu* wrappers, gpuReady, hydroMassDiag
src/core/gl-util.js makeProg, u, setGL
src/testing/        bridge-block.js (generated, 191 symbols / 28 writable)
tests/legacy/       73 oracle files + bridge-surface.json (the frozen contract)
tests/e2e/          4 Playwright specs
```

## Phase B — plugin extraction

| Batch | Nodes | State | Commit |
|---|---|---|---|
| prerequisite · param DSL to `src/core/params.js` | — | **done** | `d85b84f` |
| registry + `comb` | 6 | **done** | this commit |
| `mask` | 4 | **done** | this commit |
| `filt` | 11 | **done** | `2b6d1c8` |
| `gen` | 12 | **done** | this commit |
| `ero` | 5 | **done** | this commit |
| `effect` | 7 | **done** | local history |
| `data` | 14 | **done** | local history |
| `out` | 1 | **done** | local history |

Original extraction total: 60. Rock Fracture later became plugin 61. Digest green per batch, so a
bad extraction bisects to one node.

## D7 layered cake

| Layer | State |
|---|---|
| L0 bedrock + blends + masks | **done** — hexBlur 1.185→1.0000; L0 is the opening document, 13/13 on both lattices |
| L1 erosion (MC-3 D6 constants, MC-5 MFD6) | **done** — hillslope Laplacian was advecting on hex (1.1595->1.0000); flow drained diagonally always; MFD6 Freeman p=1.1 facets 1.81/1.67 -> 1.01/1.02 |
| L2 cover · L3 water · L4 climate/snow · L5 dressing | |

## Next, in order

Sprints 1, 2, 8 and the opening of 9 have shipped and been audited. The list below is what remains,
in dependency order.

1. **S9.3** — import metadata and provenance sidebar, closing Sprint 9's opening trio.
2. **S3 — cover layer**: hydraulic state outputs, regolith, cover-aware transport. This is the first
   story of the physical stack and everything in S4–S5 sits on it.
3. **S4 — water and rivers**, including S4.7's Gerstner renderer.
4. **S5 — climate and snow**, which closes 9 of the 11 genuine aux-map debt rows.
5. **S6 — export and format writers**, replacing the 8-bit PNG path the File menu still mislabels.
6. **S7 — geology and regimes**, including S7.6 Boundary Landforms.
7. **S9.4–S9.9** — global substrate, bounded evaluator, arbitrary dimensions. Three measured
   substrate defects block anything paged and must be fixed first: `GPU.rt()` never frees and
   `applyWorkingResolution` does not invalidate it; `GPU.prog()` caches by key ignoring source;
   `atFeatureScale` mutates the global `RES` in place, so it is not re-entrant.
8. **S10** — capability tiers, streamed pages, clipmaps, GPU-only paged evaluation, Walkaround.
   **S10.R0 calibration runs first and in parallel**: Sprint 10 is not Ready until both
   `gpuParityMaxMismatchFraction` and `antiTilingMinReduction` are frozen from measured controls.

An audit runs after each sprint. The Sprint 8 audit is the reason six stories were rebuilt rather
than ticked, and it is the strongest evidence so far that the audit is not a formality.

## Open, carried

- `_verify_realtime.js` reports 0 PASS / 0 FAIL — a report-style probe with no assertions, so it
  cannot fail. Same family as `_verify_glsl_probe` before it was gated.
- `lift-glsl-source.js` considers only the **first** occurrence of a signature per file, so a decoy
  in an HTML comment ahead of the live definition would win; and a `src/` file the page never
  imports could be the sole lift source. Both need the import graph to close properly.
- C11 square-shape audit: 8 sites still open in `_verify_hex.js` (measured domain-restricted, not
  corrupted), `_verify_hex_sampling.js`, `_verify_hex_dem.js`; plus 117 latent sites in square-only
  oracles.
- **19 commits are not on the remote** as measured on 2026-08-02. Push has never been authorised.

---

## Water: S4.7 closed, plus four defects the user's screenshots found

S4.7 is complete and gated. Getting there turned up four separate defects, three of them in code
that had already passed its own gates — worth recording because the pattern is the same each time:
**a gate that measures the wrong quantity passes on a broken build.**

| # | Defect | How it was caught | Gate now |
|---|---|---|---|
| 1 | Gerstner controls (wave height, sea state, body kind) were never built, so the preset expanded at 1.2 m on a 5 km world — correct and invisible | user screenshot: "this is liquid water" | `_verify_water_displacement.js` — the signal must SCALE with the authored height |
| 2 | The analytic wave normal was computed by both vertex shaders and **read by neither**. Water was displaced by 12 broadband waves and lit by 2 plane sinusoids | user screenshot of the banding | `_verify_water_banding.js` — median local-peak autocorrelation, 0.369 → 0.000 |
| 3 | Detail slope spectrum ASCENDED (0.390/0.462/0.546, +18.5%/octave) so the finest octave drove the normal; all three octaves shared one lattice orientation; the sparkle field had a 7.854 s global period | arithmetic on my own new code, prompted by research | not directly gated — see Open |
| 4 | Shoaling was INVERTED: amplitude faded to zero as depth fell, so the sea was glassiest where real water is roughest | user: "real water has waves on the shore … take shoal into account" | `_verify_shoaling.js`, 4/4 armed, one mutation replays the original defect |

Defect 4 recurred *while being fixed*: the first implementation referenced the onset of shoaling to
wave **height** instead of half the **wavelength**, so the breaking limit bound before Green's law
could lift anything and the wave never actually grew. The gate caught it because it asserts the peak
*exceeds* the authored height — "amplitude varies with depth" would have passed the broken version.

Four measurement errors were made building the banding oracle alone, all recorded in the file: a
plain autocorrelation maximum (measures smoothness, not periodicity); a 41 px high-pass narrower than
the 63 px band it had to preserve; a pixel population selected by "the ripple changed this pixel",
which fragments the run at every zero crossing of the signal being measured; and scanning rows only,
which is blind to bands running along the scanline. It also first ran at −4.5 °C, where the sea is
ice and there are no ripples at all — now an explicit liquid-water assertion.

**Now shared, generated, injected into both passes** (the rule that already governed the geometry):
the Gerstner terms, the detail layer, and the shoaling law. Before this, `waveData` was hand-copied
into two shaders and was the one piece of water GLSL outside that rule — and the piece that rotted.

### Open

- **W18c** — the detail layer's octaves are below 1.5 m, so at overview zoom (~10 m/px) they fade to
  nothing by design and the `strength` dial is close to a no-op there. Correct physically; means the
  visible band at that distance is entirely the swell. Whether the dial should retarget to a
  view-relevant band is a product question, not a bug.
- **W19/W20** — stylized (BotW-style) and realistic upgrades. Research landed with sources; the
  highest-value items are a world-space (not screen-space) depth ramp for banded colour, Roystan's
  normal-compensated shoreline foam, and slope-variance specular AA to replace the fixed exponents.
- Defect 3's fixes (descending spectrum, per-octave rotation, aperiodic sparkle) are verified by
  arithmetic and by the banding oracle staying at 0.000, but none has a mutation of its own.

---

## Sprint 4 audit — verdict: NOT CLOSEABLE

Four auditors plus adversarial cross-checks. The synthesis agent died on the session limit, so this
is assembled from the six that completed; treat story-level counts as indicative and the individual
findings below as evidence-backed (each carried a command and its output).

**The headline is not that stories are incomplete. It is that several gates are green on claims they
do not test.** Four failure modes were named up front and the audit found all four still present.

### Confirmed UNSUPPORTED, with evidence

| Story | Clause | Finding |
|---|---|---|
| S4.1 | acceptance gate is `_verify_depression_policy.js` | that file does not exist; the assertions live in `_verify_physical_flow.js` |
| S4.1 | "Fill raises each basin **exactly to its lowest spill**" | the oracle asserts `fillRaised > 40` — a *count*. The level is never compared to the spill at all |
| S4.1 | analytic **nested**-basin fixture | no nested fixture anywhere. A probe shows the code is correct; nothing tests it |
| S4.1 | `conditioningDelta:m`, physical units | declared `unit: 'none'` in ports.js, not metres |
| S4.1 | emit basin IDs and spill features | the node declares four outputs; neither is among them |
| S4.2 | "assert all output units/ranges" | no range or unit assertion on any emitted port |
| S4.3 | movable point/spline objects | no placement editor exists; the only authoring surface is a text parameter |
| S4.3 | undo/redo | not implemented |
| S4.5 | NaN discharge guard | the module states the guard; an injected defect passed |
| S4.5 | lattice-mismatch refusal | unarmed |
| S4.6 | accepting the offer adds a visible undoable branch | one call site, not reachable from the app |
| S4.7 | "sampled displaced vertices remain inside inflated bounds" | `presetBounds` is never called by the renderer |
| S4.7 | "displaced silhouette **instead of** a flat plane with animated normal noise" | **the evidence oracle cannot tell the two apart — zeroing the vertical displacement does not fail it** |
| S4.8 | all clauses | not implemented. GGX was written, verified against a CPU oracle, and reverted for blowing the sea to white |
| S4.9 | ice, causal foam, no-ocean-swell-on-rivers | green in the module, UNSUPPORTED in the shipping renderer |

### The pattern, and it is the same one all sprint

Three of the four named failure modes recur here, and the S4.7 row is the worst instance yet: an
oracle that measures *something changed on screen* while the story's claim is *the geometry moved
rather than the shading*. Zeroing `d.y` — deleting the entire displacement — leaves it green. That
is the S4.10 evidence gate certifying the exact thing S4.7 exists to rule out.

The recurring shape across all of them: **the module is gated, the renderer is not.** S4.9's ice,
foam and river-swell clauses are all about pixels and all asserted against the core. So is S4.7's
silhouette. A core module can be perfect while the shader ignores it — which is precisely what the
deferred-normal defect turned out to be.

### Exit gate

Sprint 4 does not close. Blocking, in order:

1. **S4.7's evidence oracle is vacuous on its central claim.** Fix first; everything else is
   ordinary incompleteness, this one is a gate asserting something untrue.
2. S4.1's fill-to-spill assertion is a count, not a level.
3. S4.8 unimplemented.
4. The module-versus-renderer split in S4.9: either gate the shader or move those clauses to S4.10
   and mark them open. They must not stay green where they are.
5. S4.3's authoring surface (placement, undo/redo) — real work, honestly absent rather than
   mis-gated.

### Not confident about

The synthesis never ran, so there is no single ranked cross-checked list; two of four cross-checks
also died. One auditor argued some S4.5 items were graded against module comments rather than the
sprint doc's three acceptance bullets, which would inflate that story's failure count. Re-run the
audit when the session limit resets.
