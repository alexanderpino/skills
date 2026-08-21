# Gauntlet contract — sea and open water

Carried forward from nine hand-rolled waves, at the point the rewritten
`gauntlet-loop` skill was adopted. The archived state is
`legacy-config.json` and `legacy-rounds.jsonl`; the schemas differ and the
history was **not** reformatted backwards, because reformatting nine waves of
records buys nothing the skill's own mantra would fund.

## Goal

TWO deliverables that prove each other.

1. The **terrain-renderer skill reaches AUTHORITY** on sea and open water — the
   mathematics, the pseudocode and the inference rules present, every figure
   with a provenance mark, every claim either derived, cited, or marked open.
2. The **reference implementation reaches HYPER-REALISM** — renders a viewer
   would have to wonder about.

Neither alone is the goal: a chapter nobody implemented is untested, and a
render nobody can derive is a picture. The render proves the chapter; the
chapter explains the render.

## The contract, owner's ruling

**THE THEORY GOES IN THE SKILL AND THE CODE PROVES IT.** Every claim in a
chapter must have a code path that demonstrates it — offline **or** through a
rasterizer, and the choice is a decision, not a default. A claim with no
implementation is a claim nobody has tested.

The consequence names the project's largest unproven region: **the offline
reference proves the PHYSICS, and nothing proves the APPROXIMATIONS.** The
chapter's real-time half — the fullscreen-triangle pass, LOD and surface
geometry, what to pre-cook, the LUT factorisation law, distance and filtering,
transparency and pass ordering, the engine-native water architecture — is
written, cited and provenance-marked with **zero lines of code behind it**. A
rasterizer reference proves what the offline path cannot, because approximation
error is invisible to a path that does not approximate.

## Target bar

`bar/bar.md` — sections A–L against the owner's Aljezur photographs, plus the
section-A arbitration. Frozen; read it from the file, never from a
restatement.

Target score **7**. The stretch is the hyper-realism criteria below, and it is
a real bar rather than a mood:

- **FRAME TO MATCH.** A reference render is shot from a viewpoint one of the
  owner's photographs was taken from, at the same framing, so the two can sit
  side by side. A render at a viewpoint no photograph shares is illustration.
- **NO PLACEHOLDER IN A HERO FRAME.** A caption admitting a placeholder is the
  right discipline for a diagnostic and disqualifying for a reference.
- **THE TELL IS USUALLY NOT THE WATER.** A single synthetic element anywhere in
  frame fails it, and it is usually the sand, the rock, the foam edge or the
  horizon.
- **ONE CODE PATH.** Every hero frame comes from the same code and the same
  constants. A frame tuned for its own viewpoint proves nothing about the model.

## Inspection, and which dimensions have machine gates

- **physics** — machine-gated. `pool-suite` and `sea-suite` in `config.json`
  run the two `validate*.py` suites; a physics dimension a suite can decide is
  decided by the suite and logged `--mode rubric` with the row counts as
  evidence. No critic confirms what a suite already printed.
- **visual** — not gateable. This is where a separate critic is spent, and the
  only place a builder's self-report is weakest.
- **prose** — the chapter against the bar; gateable only for provenance-mark
  coverage, judged otherwise.

Measure in **scene-linear, before the tone map**. Never read a PNG for physics.

## Standing rulings

1. **THE PURPOSE, before every other ruling.** A reference implementation
   exists to PROVE and to IMPROVE the theory and mathematics in the skill. It is
   an instrument, not a product. Three consequences bind every wave: **(a)** a
   wave's deliverable is a **verdict on the skill's claims**, not an artifact —
   "it renders" is not a deliverable; **(b)** a finding that stays in the
   implementation's README is **half-delivered** — anything touching the theory
   must reach `references/`; **(c)** the traffic runs **both ways** and both
   directions are wins, and a claim that survives a serious attempt to break it
   is worth recording as survived.
2. **Every wave produces visual evidence** into `gauntlet/sea/evidence/`. Owner
   ruling, and the pool loop under-delivered on it.
3. **The physics comes from physical effects**, never from a constant chosen to
   make the picture right. Owner: *"Het moet komen door natuurkundige effecten."*
4. **The geometry stays analytic** — a Dean profile and analytic solids. A
   sculpted mesh is unverifiable and ends the project's central claim.
5. **The wave field arrives from OUTSIDE** with a stated offshore spectrum, so
   shoaling and refraction are outputs and not inputs.
6. **The pool does not disappear.** Shared physics is imported, never copied;
   the pool's frames stay bit-identical and its suite stays green.
7. **Do not calibrate against the photographs.** They carry three camera
   failures and one unresolved eclipse; the target is the closed form. The
   photograph sets the framing and the scale, not the constants.
8. **A wave may conclude that a previous wave was wrong, and that is a good
   outcome.** Budget for it: on the pool loop the highest-value waves added
   nothing and found something already there was broken.
9. **Consult terrain-architect before inventing terrain.** The bathymetry, the
   morphodynamic loop and the coastal IOPs are its material, and the two skills
   already share `γ ≈ 0.78`. Reconstructing any of it from memory is the failure
   this project exists to prevent.
10. **Watch the radiation-stress factor of two:** the longshore thrust is
    `E_0/4` in DEEP-WATER quantities and `E_b/2` in BREAKING-ZONE quantities,
    because `c_g/c` is 1/2 in deep water and 1 at breaking. Pairing the quarter
    with breaking-zone values is wrong by exactly two.
11. **PRUNE, and do not chase 10/10.** Owner ruling on the gauntlet-loop skill:
    it bogged down in continuous review and did not cut unpromising paths fast
    enough. A gap that has survived two waves **with its mechanism named and out
    of scope** is parked with the reason recorded — the naming is the
    deliverable. (The rewritten skill now carries this as `no-progress` and the
    park rule.)
12. **BUILDERS PUSH THEIR OWN WORK.** The container re-provisions without
    warning and restores the clone to an older commit; the remote is the only
    durable state. Commit and push as soon as a coherent unit exists, and
    re-fetch before starting.
13. **~~RUN LONG JOBS IN THE FOREGROUND.~~ — WITHDRAWN AT WAVE 18, MEASURED
    FALSE.** This ruling claimed a backgrounded process gets about *22 seconds
    of CPU per ten minutes* of wall clock while a foreground call gets the full
    machine. **It is not true.** Measured directly, a busy loop backgrounded
    through the same tool returns **89.9 s of CPU in 90.0 s of wall clock —
    100%** — and a foreground loop returns 19.9 s in 20.0 s. There is no
    throttle in either direction.

    The ruling shipped in **every builder brief for six waves** and shaped how
    every one of them ran its suites. A builder finally contradicted it with its
    own measurement (*"a backgrounded suite ran at ~104% CPU"*) and named the
    real cause in the same breath: **three of its own stale processes surviving
    a `pkill`, and cross-builder contention on 4 cores.**

    That is this project's own error class, committed by the lead agent: **a
    number measured once, under conditions nobody recorded, written down as a
    property.** The original observation was almost certainly real — several
    concurrent builders each running a ~400 s suite on four cores will each see
    a fraction of a core — but the *explanation* was invented and the number was
    generalised from one state.

    **What survives, for a different reason:** `nproc` is **4**, and a wave
    routinely has three builders plus the lead running suites. Long jobs still
    should not be casually parallelised, and a suite total taken while four
    others are running is not comparable to one taken alone. That is
    **contention**, which you manage by not running four suites at once and by
    saying what else was running when you took a total — not by avoiding the
    background.

14. **A near-zero measurement is worthless until zero has been shown to be
    reachable.** Wave 9's ruling — the fourteenth way a measurement lies, with
    the sign flipped. Build the control whose answer is known in advance; wave 9
    found a 24× error in `transform_2d` that 301 suite rows could not see, and
    found it only that way.

## Budget and autonomy

- **15 waves** agreed at intake; **9 spent** under the hand-rolled loop. Token
  budget **not agreed** — `status` will say `tokens: not measured` until one
  round is measured and a ceiling is set, which is the honest reading and a poor
  one.
- **Autonomy: run unattended.** Owner: *"BLijf maar gewoon door gaan met de
  waves, autonoom. Zorg voor visuele tussentijdse evidence."*

## ~~Closed, and not to be re-opened~~ — RE-OPENED AT WAVE 20, and the closure was a category error

The owner: *"Het oppervlak van de zee en ander open water bestaat ook uit golven.
En soms heb je hogere golven. En golven die omslaan."*

That is a correction and it lands. **Stokes' 120° corner bounds waves of
PERMANENT FORM — steady waves.** An overturning wave is precisely one for which
*no* steady solution exists; it overturns **because** the permanent form has
ceased to be available. The theorem was used here to close a question it does not
answer, and I wrote that closure.

**What the argument actually establishes is narrower and still true:** a
**single-valued heightfield** `η(x, y)` cannot carry a multivalued surface,
because a plunging lip folds over itself and a heightfield admits one height per
point. That is a statement about **this implementation's representation**, not
about the physics — and a representation is a choice.

So the two sections are re-scoped rather than closed:

- **Section F — the multivalued surface.** No longer *unreachable*. Now:
  **requires a representation this implementation does not have.** The route is
  not exotic and it is what production renderers do: the heightfield carries the
  wave up to the instant it goes multivalued, and a second representation — a
  parametric breaker lip, a mesh strip, or particles — carries the plunge. What
  it costs and what it would break is **unpriced**, and pricing it is the first
  step, not building it.
- **Section A — the backlit face.** Its geometric bound stands *for a
  single-valued surface* (30° against the 41.48° needed) and falls with F, since
  A is F at an earlier instant. Re-scoped with it. Its other half — falsifying a
  renderer that *tints* its water — was discharged by wave 4's cuvette and stays
  discharged.

**And the owner's first clause is the part that matters most.** Overturning is
not an exotic edge case to be dispatched with a citation. **The sea surface *is*
waves, sometimes higher ones, and sometimes they overturn.** A model of open
water that structurally cannot do it is incomplete, and the honest way to record
that is as an open gap with a named cost — not as a closed one with a proof
pointing somewhere else.

**PRICED AT WAVE 20 — `overturning-price.md`, and the price changed the
question.** The scout measured the scene rather than argued about it, and the
scene answers: the wave breaks on the seaward flank of its own Exner bar, at a
local slope of **1 : 4.4**, where the local Iribarren number is **ξ = 1.110
(0.967–1.203 over 89 rows) — plunging on both published threshold sets, on every
row**. So this model already says the scene overturns. Two further measurements
narrow the representation question: the shipped surface reaches **43.53°** (46.89°
in a fine zoom) — *past* Stokes' corner and past 41.48° — and section A is still
unreachable, because chapter 12's criterion is on the **sum** of two crossings,
82.96°; and `surface_state`'s validity clamp bites on **74.78 %** of the wet bay
at up to 154× the shape's own limit. **The boundary is topological, not angular.**
Two candidate representations survive standing ruling 4 and only one is
affordable — an exact parametric free surface, priced at 2 waves + 2–4 and
blocked on provenance. Sections A and F stay **open**.

**Kept as a warning about method**, because it is the more useful lesson: a
correct theorem, cited accurately, closed a question for six waves by answering a
neighbouring one. Nothing in the citation was false. The failure was in the
scope of the claim it was made to support, and no suite, critic or answer key can
see that — only reading the theorem's own preconditions can.

## Contract amendment — the goal has a third part, and the skill ships no figures

Owner ruling, added mid-run: *"Grafieken moeten toegevoegd worden aan de skill ter
ondersteuning."*

**Measured before accepting it, and it is worse than it sounds.** Across all
twenty-two chapters of `terrain-renderer/references/`, the count of embedded
figures is **zero**. There is not one image file anywhere in the skill outside
the two implementation directories. Meanwhile the loop has produced **107**
evidence PNGs. Every one of them lives in `gauntlet/`, which is run state — not
in the thing that gets read.

So a reader of the skill today gets mathematics, pseudocode and prose, and
cannot see a single one of the things thirteen waves proved.

### The goal, restated in three parts

1. The **terrain-renderer skill reaches AUTHORITY** on sea and open water.
2. The **reference implementation reaches HYPER-REALISM**, and the mathematics is
   proven by reference renderings that score **9/10**.
3. **The skill carries figures that support the mathematics.** A chapter whose
   claims cannot be seen is a chapter that has to be taken on trust, which is the
   one thing this project refuses everywhere else.

### The discipline that keeps part 3 from rotting

- **A figure in the skill is generated by a committed script, never pasted in.**
  Same rule as everything else here: the code proves it. A figure nobody can
  regenerate is a screenshot of a claim, and it will be wrong within three waves
  and nobody will know.
- **Do not dump the evidence set into the chapters.** The 107 existing figures
  were built to answer *"did this round move the number"*. A chapter figure
  answers *"what does this claim look like"*. Those are different jobs and most
  evidence figures are the wrong shape for the second — they carry wave numbers,
  open-gap notes and diagnostic panels a reader does not need.
- **Derive the figure list from the chapters' own claims**, not from what happens
  to have been drawn. A claim that would be clearer as a picture earns a figure;
  one that would not, does not.
- **Every figure carries its provenance mark**, exactly as the prose does:
  derived, cited, or measured — and which script drew it.
- **Scene-linear for anything physical**, and say so in the caption when a figure
  is display-referred on purpose.
- **No burned-in commentary.** Wave 11's three critics each reported that captions
  inside the pixels defeated the blind. In a chapter the caption belongs in the
  markdown beside the image, where it can be read, diffed and corrected.

### Ownership

This is the **`chapter` lane's** work. That lane has sat behind the WIP limit for
the whole run and has never been funded once — which is defensible while its job
was prose nobody had scored, and is not defensible now that it owns a named,
measured gap of this size.

## Two process rulings, added at wave 16 after diagnosing why the run never converged

Both came from one reading of `status`, which after fifteen waves said:

```
wave 15 of 26 budgeted | ~37 calls spent | 0 gap(s) closed | WIP limit 3
no stop condition fired
```

**Zero gaps closed in fifteen waves — and it was the bookkeeping, not the work.**
Real things had closed: the lobe exponent, the sea/sky seam, the missing
alongshore phase, the inverted wet/dry ladder, the plateau as an output. But
every round record stapled the *next* gap onto the round that closed the last
one, so `severity` was never once logged as `none`. The script counts a closure
as a clean round following a gap; it had recorded none, because none was ever
written.

That is not cosmetic. **`bar-met` and `clean-streak` are the two stops that end
a run, and both count clean rounds.** A round that fixes something and names the
next thing was being logged identically to a round that fixed nothing. The run
could not converge by construction — not because the work was not converging,
but because the record admitted no arrival.

**Ruling 15 — CORRECTED AT WAVE 18, and the script caught me.** It first read
*"a round that closes its gap is logged `--severity none`"*, and that conflated
two different things. `severity` is a statement about **the dimension against
the bar**, not about **the round against its brief**. `none` means *no
meaningful gap left*; it feeds the clean streak and therefore the stop
conditions. A round can close the gap it was handed and leave the dimension
nowhere near the bar — wave 18 did exactly that twice, and `gauntlet.py` warned
both times: *"severity is 'none' but score 7 is below the target of 9 — 'no
meaningful gap left' below the bar is contradictory."* It was right and I was
not.

**So the corrected ruling is:** log `--severity none` only when the *dimension*
has no meaningful gap left against the bar. Log progress in the **score**, which
is what moves and what the trend reads, and log the residual as the new gap —
in its own record, never stapled to the round that closed the previous one.

**And my original diagnosis was half wrong, which is worth keeping.** I read
`0 gap(s) closed` after fifteen waves and concluded the bookkeeping was hiding
arrivals. It was not: **there had been no arrivals.** What was actually true is
narrower — the record never distinguished a round that *moved the number* from
one that did not, because I was logging each lane's standing state rather than
each round's result. The score already carries that distinction and I was not
using it. The
next gap gets its own record, or goes to `backlog.md`. Never stapled to the
round that closed the previous one. A clean round is a fact about the artifact
and the log has to be able to state it.

**Ruling 16 — brief the guards and the evidence FIRST, the chapter last.**
Six builders across waves 12 and 13 died on session limits, and they all died at
the *end* of their round, because the briefs said build → guard → draw → write.
So the guards and the figures were what got lost, every time. Wave 13 landed
three lanes of real physics with **zero suite rows and zero figures**, and it
went unnoticed for two waves because the suite stayed green on code it had never
heard of.

The order is now: **guard rows → evidence → chapter**, pushed after each. A
builder that dies should lose the paragraph, not the proof.

**And the check that would have caught wave 13 in ten seconds**, now standing:
a suite total is not evidence that a wave landed. `git log -- validate_beach.py`
must show the wave's own entry. Running the right command is not the same as
running a command that could have failed.

## The generic reference set — `gauntlet/sea/bar/generic/`

Added at wave 16 on the owner's ruling that *"als je ergens een referentiefoto
van nodig hebt staat het internet vol"*. Nine openly-licensed photographs with
full provenance, plus `measure.py`, which recomputes every number in that
directory's README from the JPEGs beside it.

**It is not the bar and must never be filed as one.** `bar/bar.md` describes the
owner's five Aljezur frames; these are strangers' photographs of other
coastlines. The hyper-realism criterion — *shot from a viewpoint one of the
owner's photographs was taken from, so the two can sit side by side* — is
**still blocked** and nothing here bears on it.

What it does is convert four verbal criteria into **falsifiable numbers**, so a
critic can say *how far* rather than only *not yet*:

- **glitter interior sd 41–60 grey levels** (and 36–70 in a second frame), 8-bit
  luma in a ±10 px core strip, against the render's **1.0–2.6** — a factor of
  16 to 60, and the strongest result in the set because two independent frames
  agree
- **glitter taper ×2.0 widening toward the observer**, 38 → 75 px over 279 rows
- **foam correlation length 0.3–0.8% of the foam patch's own width**, against
  ~100% for a soft gradient
- **foam clot size q90, 10 cm to 70 cm alongshore** — a 7:1 range *within one
  wave*, scaled from a person's height
- **wet/dry sand luminance ratio bracketed 1.7× ≤ r ≤ 3.0×** by two frames
  sitting on opposite ends of the transfer curve

Every one of those is dimensionless or bracketed on purpose: **absolute
radiometry is refused throughout**, because the illuminant, exposure, white
balance and grade of a stranger's photograph are all unknown.

**Ocean colour at depth was refused outright**, with the measurement that
justifies it: one candidate's offshore water has a red-channel mean of 8.7/255,
a grade on the floor, and another is a stitched panorama whose flare makes open
sea read *brighter* than the surf. The reason is structural rather than bad
luck — every well-composed coastal photograph is graded and the grade is never
recorded. Colour stays on the daylight Aljezur frames.

**Six of the nine are share-alike.** A figure that pastes one beside a render
output is a derivative and inherits CC BY-SA. Read §9 before publishing one.

## Ruling 17 — the pictures must be in line with the physics

Owner ruling: *"De plaatjes moeten in lijn zijn met de fysica."* It arrived
while three builders were under a brief demanding a **visible change in a
rendered frame**, which is exactly the pressure under which someone draws
something that merely resembles the answer.

It is not a softening of that demand. It sharpens it: **the visible change has
to BE the physics becoming visible**, not a separate thing that looks like it.

Three consequences bind every round that touches a frame:

1. **Every added structure is traceable to a computed quantity.** For each thing
   now visible that was not before, the round names the number it came from and
   where that number is computed. *"Granularity from the resolved slope variance
   at the pixel footprint, out of `wind_spectrum`"* is a chain. *"A noise field
   tuned to sd 45"* is not, and it fails standing ruling 3 whatever the frame
   looks like. The test extends to the camera: a viewpoint must follow from
   something, and *"it shows more water"* is not something.
2. **If it cannot be derived, it is not drawn — it is named.** A round reporting
   *"the structure the photographs show requires a term this model does not
   have, and it is this term"* is worth more than a frame that looks better for
   a reason nobody can trace. That naming has been a real deliverable more than
   once here and is never a failure.
3. **The residual is stated.** How much of the measured gap closed *by
   derivation*, and how much remains. A partial close with an honest split is a
   result; a full close nobody can follow is not.

**Why now, and it is worth keeping.** The owner looked at a hero frame and said
it does not look like water. The honest answer was that seventeen waves went to
physics — which is now genuinely good — while nobody worked on the picture since
it was scored 3/10 at wave 11. The correction is to work on the picture. **The
failure mode one step past that correction is the opposite one**: a picture that
looks better while the physics behind it stays unreached. That is worse than the
current frame, because it would be untrue *and it would look fine* — and this
project's entire method depends on the render being an instrument rather than an
illustration.

### The same ruling reaches the skill's own figures, where nothing guards it yet

The figure generator imports the implementation read-only and holds no physical
constant of its own, which is the right architecture. But wave 15's builder
reported honestly that `--selftest` **cannot see anything graphical** —
`preflight` checks numbers, never pixels, so a clipped fill, a wrong axis range
or a curve plotted against the wrong variable passes every guard, and it bit
that round four times. It also reported that **nothing compares a figure to its
caption or to its chapter**, and that the chapter-09 figures have no
implementation to disagree with, so a closed form and a quadrature sharing one
misreading would agree and pass.

So a figure can be numerically correct and *drawn* out of line with the physics
it claims to depict, and the suite is silent. Under ruling 17 that is a gap in
the instrument, and it is recorded here rather than in a builder's README
because it belongs to whoever next touches `references/figures/`.

## Ruling 18 — derived, guarded, and never called

Wave 18 found this three times, in three lanes, by three builders who did not
speak to each other. It is now this project's dominant error class and it
outranks every individual defect any of them fixed.

- **Foam.** Wave 12 diagnosed the airbrush correctly, built the entire fix, and
  wired none of it. `grep` for `boolean_indicator`, `filtered_indicator`,
  `grain_radius`, `deck_source` returned **nothing outside `beach_foam.py`**.
  `shade_water` still blended by `coverage(m)` — the mean.
- **Glitter.** Seventeen waves argued the resolved/unresolved slope split, and
  `grep -rn SlopeRealisation` returned the class statement and two comments:
  **nothing had ever instantiated it.** `shade_water` computed the two variances
  on one line and threw them away on the next.
- **Diffraction.** The physics critic established it independently: ten Sommerfeld
  rows verified, and `beach_render.py` **does not import `beach_diffract`**.
  Zero pixels of either hero frame carry a diffracted edge.

And one more, from the wave before: **wave 13 landed three lanes with no suite
rows at all**, and the 413-pass total that "confirmed" it was wave 12's suite
unchanged.

**The suite cannot see any of these, and the reason is structural rather than
sloppy.** Every row tested a *function* in a module. Not one tested whether the
**render path reaches it**. A module can be correct, guarded, cited, figured and
chaptered while contributing nothing to a single pixel, and every instrument the
run owns will report success.

**So: a row that tests a function must be paired with a row that tests that the
frame reaches it.** Coverage is a first-class property here, not a nicety —
integers, off the rendered buffer: how many pixels, what share of frame, and
where. The physics answer key says in its own words that it *cannot* check this,
because it checks quantities and not whether any pixel reached the code, and the
project has a shade sail on record that **0 of 8 640 000 subsamples** ever hit.

**The ten-second version, for a lead agent reading a builder's report:** a suite
total is not evidence that a wave landed. `git log -- <the suite file>` must show
the wave's own entry, and a `grep` for the new symbols must find them **outside**
the module that defines them. Running the right command is not the same as
running a command that could have failed.

**Lifted to the chapter, and it is NOT a fifteenth way.** The ninth way — *the
code no pixel reached* — was already there, with the shade sail as its instance.
This is a **second shape of the ninth**, and the distinction is the detector:
the ninth's instance is coverage zero *by scene configuration*, where the code
is wired in and this frame's geometry never asks for it. A per-branch subsample
counter finds that one. It cannot find this one, because the branch it would
count sits in a module nothing calls, so it is never compiled into the frame's
execution at all — **the count is not zero; there is no count.** The detector is
a `grep` that must find each new symbol *outside* the module defining it, and a
reach row paired with every function row. Written into
`11-verification-failures.md` under the ninth way, with all four instances.

## Ruling 19 — the targets are re-cut, and the extension waits for evidence

Owner delegated the target after the re-quote: *"Neem de beste stap en meest
realistische stap."* Owner also chose **both halves of the overturning wave** and
**is supplying the five Aljezur photographs**.

**Targets are now `physics=9, visual=7, prose=8`.** Physics sits at 8 with two 9s
— one honest step. Prose is at 8, judged twice, and that is the target. Visual
moves to **7, not 9 and not 6**: 9 is not buyable at any budget the arithmetic
allows, and 6 was only ever justified by the missing photographs, which are now
coming. 5 → 7 is one honest step on the measured trajectory.

**The extension was NOT taken, and the script is the reason.** `extend` refused:

> budget is not depleted (wave 19 of 26) — **extend when it runs out, so the
> decision is made on evidence.**

That is better discipline than the plan had. The plan priced the chosen scope at
**8–11 waves and ~8.4–12.1M tokens** at the measured rate of 7.0 rounds and
~1.23M tokens per closed gap, against 7 waves and ~1.8M remaining — so an
extension is very likely, and it will be requested **when the stop fires**, with
the run's own evidence behind it rather than a projection. Not forced.

**And one correction the run should stop repeating.** The lead agent told the
owner the figure programme was "under a quarter done" because 5 of 22 chapters
carry a figure. `00-index.md` says otherwise in its own words: the twenty-chapter
gap is deliberate, with per-chapter rejection reasons recorded, and *"the
remaining chapters — `02`–`05`, `13`–`18` — have no implementation behind their
quantitative claims anywhere in this skill … an invented number in a figure is
worse than no figure."* **The figures programme is complete for every chapter
that has an implementation behind it.** The residue is not a figures gap; it is
the contract's own *nothing proves the approximations*, and it is one item.
