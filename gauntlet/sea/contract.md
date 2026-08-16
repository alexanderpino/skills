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
13. **RUN LONG JOBS IN THE FOREGROUND.** Measured in this container: a
    backgrounded process gets about **22 seconds of CPU per ten minutes** of wall
    clock, while a foreground call gets the full machine. The sea suite takes
    ~9 minutes foreground and effectively never finishes backgrounded. One wave
    lost an hour to this and reported a suite total as the sum of two partial
    runs rather than one.
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

## Closed, and not to be re-opened

- **Section A** — the backlit wave face reading green against grey-blue water.
  Closed as **unreachable by proof**, not parked as unreached. Stokes' 120°
  corner (1880) caps a single-valued crest face at **30°** for every wave of
  permanent form, at any order, at any depth, against the **41.48°** an in-water
  lengthwise sightline needs. Section A requires the wave to be within ~11° of
  overturning, which is section F's multivalued instant: **A and F are one
  criterion at two moments.** Section A's other half — falsifying a renderer
  that *tints* its water — was discharged by wave 4's cuvette and stays
  discharged.
- **Section F** — the multivalued surface. Out of scope by the same argument.
