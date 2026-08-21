# Backlog — noticed, deliberately unfunded

One line each. This is where an **item** goes when it is out of scope. It is not
`config.json`'s `parked`, which is coarser: a park stops funding a whole
lane × dimension pair, and using one to record a single item defunds everything
else in that pair. Both entries below were parks until wave 10 caught the
mis-scoping — between them they had taken diffraction and the concentric ramp
out of the budget, which are gaps 3 and 5 of fifteen.

The report carries this file as work the user can choose to buy. Never as scope
this run added.

---

- **Section B, the second breaking line.** Three waves. Mechanism named and out
  of scope: `Γ_eq` sits above `γ_s` on a shoaling bed, the trough is one
  dissipation e-folding wide and the reform needs two, so the missing mechanism
  is the **2DH rip-feeder circulation** — which terrain-architect chapter 12
  declares out of scope. Wave 3: zero of 89 rows reform on a computed 2-D bay,
  so it is not geometry. Wave 5 fired one more thing at it and it survived — the
  derived `UR_HALF` makes the bar 33% higher in relief and 15 m further seaward,
  and the minimum `H/d` in the trough moves 0.4556 → 0.4571 against the 0.40
  needed. **A bigger bar is not the missing mechanism.** Closing it means a 2DH
  solve. The naming is the deliverable.

- **Hsu & Evans' parabolic bay-shape equation.** Parked on **provenance, not
  difficulty** (wave 9). Fifteen fitted quartic coefficients, no internal check
  that would catch a wrong digit, and no paper in this container. The circular
  arc and the logarithmic spiral *are* derivable, and were built and measured
  instead. Unpark only when someone can put the paper in front of it — never by
  reconstruction. Standing ruling 9: consult the source or do not invent it.

- **The eclipse's contact times at this longitude.** Until settled, the surf
  frames are not radiometric evidence. Open since intake.

- **The suspended load's size distribution at Aljezur.** Wave 6 closed the two
  decay timescales and found there are three, one of which is not a number; the
  distribution itself is still open and routes through 28-liquids' Babin bridge
  once the cuvette inversion gives `b`.

- **No backwash frame exists.** Section D rests on owner testimony alone.

- **`optics.slab_esc` / `slab_trap` quadrature.** ~6e-5 structural error from one
  Gauss–Legendre rule across the kink at the critical angle; the guarding row
  tolerates 1e-4, which is *exactly the size of what it covers*. Found
  independently by two builders. A tolerance the size of the defect is the
  twelfth way in chapter 11.

- **The hero camera follows the terrace onto the terrace.** Found at wave 16
  while re-measuring the plateau. `beach_camera` stands the eye on the highest
  ground the bed supplies, which is bar J's own constraint and not a
  composition; the sea-level history raises the highest ground from a 17.31 m
  cliff brow at x = 648 m to the 30.19 m oldest tread, which reaches the
  landward boundary. So the inference walks the camera onto the flattest surface
  in the domain: **water falls from 16.8 % to 1.6 % of the frame and 66.4 % of
  it is one tread.** Not this round's to fix and not the terrace's fault — the
  terrace is correct. Closing it means the camera inference needs a term the
  landform cannot supply on its own (a standoff, or a rule that the eye wants
  the *cliff brow* rather than the *highest point*), and that is a camera-lane
  decision with 413 published measurements standing behind the current
  placement. Evidence: `s16-terrace-frame` against `s16-terrace-fixedcam`.

- **`through_face`'s `chord > 0` clause is an invariant with no exercise.**
  Wave 16's `--bugs-seam` removed it alone (`seam-no-chord-clause`) and **not
  one row fired**: no ray on either hero frame is entered-and-exited with a zero
  chord, so the clause is true and inert on this bed. It is kept because it is a
  statement about the medium rather than a filter, but the suite cannot tell
  whether it is right. Closing it means a bed or a camera where a ray crosses a
  face at exactly zero range — a tangency — which nothing in this scene
  produces.

- **The transport reads one of the two moments its own wave shape carries.**
  `terrain-architect/references/12-glacial-coastal.md` names this in its own
  words, measures it — `(1 − f_brk)` is a straight line standing in for `cos ψ`
  and reads **29.3 % low at half breaking** — and the code has not followed it.
  `grep` at wave 19: `beach.surface_moments` computes `As`, **nothing in
  `sediment_flux` reads it**, and outside `beach.py` the symbol appears only in
  the suite. The missing half is the acceleration-skewness transport (Hoefel &
  Elgar 2003), which is the published mechanism for onshore bar migration and
  the natural candidate for an INNER bar. Not closed at wave 19 because it moves
  every bar depth in the file and needs its own round with its own controls; the
  chapter's `Sk² + As² = g(r)` invariant means the total third moment is fixed,
  so this is a redistribution and not a new source.

- **The wind sea's two Pierson–Moskowitz coefficients are recalled, not read.**
  `PM_HS_COEF` and `PM_WAVE_AGE` in `beach.py` carry the second offshore
  partition, and wave 19 defended them with a sweep (±50 % in `H_s`, ±40 % in
  `T_p`, the separation criterion holding throughout) rather than a citation,
  because no copy of Pierson & Moskowitz (1964) was reachable. The *form* is
  forced by dimensional analysis and is not at risk; the two numbers are.

- **Two breakpoints on the bed, one band of white on the water.** Wave 19's own
  residual, measured twice by two instruments: `H/d` bottoms at **0.4389**
  against the 0.40 cessation needs, and in the rendered buffer the shoreward
  breakpoint's ±15 m window holds **2301 px of deck with the second partition
  and 2303 without** — the wind sea breaks inside the swell's saturated surf
  zone, where the roller fraction is already 1. Separated lines need white water
  that *stops*, which needs the wave to un-break, which needs the trough to be
  two Dally e-foldings wide, which needs the rip-feeder circulation of a 2DH
  solve. Unchanged since wave 2 and still the same exclusion.
