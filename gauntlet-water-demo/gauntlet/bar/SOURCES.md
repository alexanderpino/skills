# Bar sources — where the bar came from, and what was searched

## visual-fidelity

- **Bar artifact(s):** `bar/water-fidelity.md` — an acceptance-criteria bar, six
  "must be visibly true" claims and four "must not", each checkable in one still.
- **Where it came from:** distilled from
  `terrain-renderer/references/12-water-rendering.md`, which is itself sourced
  (Pope & Fry for the absorption ramp, Cox & Munk for glitter width, Dierssen
  for foam albedo, the chapter's own Mie-regime derivation for the plume). The
  *situation* being barred — shallow water over rock ledges with milky aerated
  clouds where waves break — comes from photographs supplied at intake.
- **Searched:** the chapter was searched for every criterion so each names a
  mechanism rather than a taste. **Not searched this session:** external
  photographic references beyond the intake images, because the intake images
  already fix the situation and the chapter fixes the physics. This is a
  deliberate, stated limit, not an assumption that none exist — for a
  photorealism goal reality is thoroughly photographed and a longer run should
  freeze several stills per case (`bar-selection.md`).
- **Cases covered:** shallow water over rock, daylight, above-water shallow
  camera angle, breaking/aerated water against rock, wet rock at the waterline.
- **Cases NOT covered:** open-ocean deep water, storm sea states, underwater
  camera, night/low sun, river flow, and animation quality over time (the bar
  judges one still). Any lane that ends up working on those needs its bar
  extended *before* the round runs, not a stretched verdict from this one.

## visual-fidelity — lane `floating-object` (added mid-run, announced)

- **Bar artifact(s):** `bar/floating-object.md` — a separate file, not an edit
  to the frozen `water-fidelity.md`. That bar named "a floating object" as an
  uncovered case; this is that hole being filled *before* the lane runs, which
  is the whole point of keeping an uncovered-cases list.
- **Where it came from:** the situation from a reference photograph supplied at
  intake (a yellow inflatable ring on a pool surface, near-overhead). The
  criteria come from `12-water-rendering.md` (depth fade at contact, refraction
  and absorption of the submerged part, caustic occlusion) and from `19`'s
  one-evaluator rule (the object must sit on the same wave function the
  renderer draws).
- **Searched:** the two chapters, for the mechanisms behind each criterion.
  **Not searched:** further photographic references for the floating-object
  case — one intake image fixes the situation, but a longer run on this lane
  should freeze several (calm vs rippled, overhead vs shallow angle) before the
  lane's verdicts are trusted far.
- **Cases covered:** a single floating object at rest or drifting slowly, in
  daylight, on water the run already renders.
- **Cases NOT covered:** the object's own material realism (inflatable vinyl,
  seams, wear), buoyancy dynamics over time, wave interaction at the object's
  own scale (it displaces water; that is fluid-sim territory, `19`), and
  multiple interacting objects.
