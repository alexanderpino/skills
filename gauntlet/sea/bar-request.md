# Intake request — what this run needs before wave 1

Two kinds of input, and the loop must invent neither: **comparison material**
(the bar, always required) and **direction** (the decisions, required when the
artifact has structure beneath its surface).

## 1. Comparison material — the bar

Bar kind agreed at intake: **reference**
Already frozen in `gauntlet/sea/bar/`: `bar.md`

A gauntlet's output is "A or B is better". Without a B that exists outside
this run, every verdict measures the builder's own taste. So this run does not
start until the material below is in place — or until the user decides the run
is not worth it, which is also a valid answer.

### What a usable bar must satisfy

1. **External** — it exists independently of this run and of the agent's opinion.
2. **Inspectable** — a critic can open, run or measure it, not just read about it.
3. **Unarguable** — the artifact cannot talk its way past it.
4. **Reachable** — the distance from today's artifact is closeable inside the budget.

### Per dimension

### physics  (target 9/10)

- **What would settle it** — **ANSWERED, and the comparator is not a photograph.**
  It is the literature's closed forms: external to this run, inspectable,
  unarguable, and already the thing every wave has been measured against. They are
  currently *scattered across four chapters and thirteen round records*, which is
  why physics has been scored on builder assertion rather than on anything a critic
  could open. The deliverable is ONE frozen answer key — every checkable statement,
  its source, its expected value, its tolerance. Named non-exhaustively from what
  this run has already used or is about to: Kelvin's wake half-angle
  `asin(1/3) = 19.4712°` (1887) and its finite-depth widening in `Fr_h`; Cox &
  Munk's mss and the `width/√mss` invariance; Battjes & Janssen's `Q_b`; the
  breaker index `γ ≈ 0.78`; Dean's `h ∝ x^(2/3)`; Green's `H ∝ h^(−1/4)`; Snell
  with `c(h)`; Sommerfeld's half-plane with `K_d = ½` on the shadow boundary and
  the Cornu limits; Longuet-Higgins' `cos^(2s)(θ/2)`; Walsh's
  `n²(1−R_int) = 1−R_ext` with `R_ext = 6.669%` and `R_int = 47.617%`; Monahan &
  Zietlow's 3.85 s; the Babin bridge `b_p(555)/SPM ≈ 0.5 m²/g`.
- **Acceptable forms**: the answer-key route in `bar-selection.md` — a
  research-backed spec authored before the round it judges, the answer key frozen.
- **Where it goes**: `gauntlet/sea/bar/physics/` (frozen; read-only once the wave starts).
- **Done when**: a critic given only that path can score our artifact against it
  without asking anyone what "good" means.
- **Status: NOT YET WRITTEN, and it is the highest-value unbuilt thing in the run**
  — it turns thirteen waves of "the builder says it holds" into something
  checkable by someone who did not build it.


### visual  (target 9/10)

- **What would settle it** — **ANSWERED, AND BLOCKED, and the block is not a
  wave.** The comparator is the owner's photographs of this coast: fifteen-plus
  frames, now including section M's two wake frames. They are the right bar —
  external, unarguable, at the right framing. **They are not on disk.**
  `gauntlet/sea/bar/` holds `bar.md`, which is my *written description* of them,
  and a description is the one thing a bar may not be.
- **What that costs, measured rather than asserted.** All three wave-11 critics
  reached the same conclusion independently, and one stated it exactly: gross
  failures against criteria the bar states IN WORDS need no pixel comparison, but
  *"a verdict in the 6-8 band would not be honest without the images, and I would
  refuse to write one."* So this dimension is judgeable from 0 to about **6** and
  un-judgeable above it. **A target of 9 is not purchasable at any price** until
  the files are placed.
- **Where it goes**: `gauntlet/sea/bar/visual/` (frozen; read-only once the wave starts).
- **What is needed from the owner**: the image files themselves, at native
  resolution, with whatever EXIF survives. Nothing else — not a re-description.
- **Done when**: a critic given only that path can hold a render beside a
  photograph. Until then, every visual round is logged with its ceiling stated.


### prose  (target 8/10)

- **What would settle it** — **ANSWERED, and it already exists in this repo.**
  `terrain-architect/references/` — a sibling skill written to the same standard,
  by the same conventions, and *not by this run*. It satisfies all four tests:
  external to the loop, openable, unarguable about register and provenance
  discipline, and demonstrably reachable, because the terrain-renderer chapters
  are already written against it.
- **The specific checkable properties**: every claim derived, cited or marked
  open; every figure carrying a provenance mark; `?` used for a genuinely
  unresolved quantity rather than a guess; corrections left visible rather than
  deleted; and no claim stated that no code path demonstrates — the contract's
  own rule.
- **Where it goes**: `gauntlet/sea/bar/prose/` — a pointer naming the exact
  chapters and properties, not a copy.
- **Done when**: a critic given only that path can score a chapter without asking
  what the house style is.
- **Status: cheap and unblocked** — the one dimension whose bar can be finished
  today.


Bring the real thing, not a description of it: a paraphrased bar drifts every
time it is restated, and drift always makes the bar easier. Capture references
at comparable framing and resolution to our own output. If the best available
comparator is weaker than the ambition, say so — a run against a soft bar that
everyone believes is hard is worse than no run.


## 2. Direction — the decisions (skip for a flat artifact: a README needs none)

A gauntlet improves; it does not decide. Where the artifact has layers, the
decisions beneath it must exist before the lanes are cut, or each fresh builder
answers the same silent question differently and the smoother pays for it every
wave (`decomposition.md`).

**First: ask whether it already exists — do not assume it must be written.**
Found in this repo already, before anyone writes anything new:

- `README.md`

Read those first. Say which are load-bearing and current, and ask only for
what they do not answer — an existing convention beats a fresh document,
because the codebase already agrees with it.

- **What is needed**: the load-bearing decisions only — the ones no lane-level
  round could reach. Where a boundary sits, what owns what, how things are named
  and addressed, dependency or update order. Not a full design document.
- **Acceptable forms**: a wayfinder map, an architecture record (SAD, ADRs), a
  spec, a design doc, or the conventions of an existing codebase cited by path.
- **Open decisions must be listed as open.** An unresolved question is not a
  default; name it so it is resolved or ruled out of scope before wave 1.
- **Where it goes**: the contract's rules — it binds builders. It is *not* the
  bar: critics do not score against it. Anything in it a command can check
  (dependency direction, forbidden imports, file placement) becomes a gate, so
  the structure is enforced free every wave instead of trusted.
- **Done when**: a builder handed only that path knows which layer its change
  belongs in and which conventions it must follow, without asking anyone.

Who can produce it: the `wayfinder` skill (map and answer key), an architecture
skill, a domain skill for this field, or grounding where the domain is solved.

## Notes for whoever fetches this

Answer-key route only: deliver ONE map (the resolved decisions and why) and ONE
answer key (the checkable statements), never a ticket file per decision — the
answer key is the bar, and a bar is one frozen file a critic opens, not fourteen.
State each item as something checkable, and mark which dimensions it cannot
cover (taste, feel, visual craft) so those get a reference artifact of their
own instead of passing by default (bar-selection.md).
