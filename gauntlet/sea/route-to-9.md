# The route to 9 — written at wave 19, because there was not one

The owner: *"Het is alsof deze open water loop weinig opschiet. Alsof er weinig
plan is."* Both halves are correct and the record proves them.

## What the record actually says

```
wave 18 of 26 budgeted | ~51 calls | 4 gap(s) closed | 60% of the token budget
```

**Every visual score logged since wave 11 was written by the lead agent from the
builders' own self-reports.** The three `3/10`s are critics'. The four `7`s are
not. `optics/visual` — which owns the glitter path, the single largest tell in
frame — **has never been re-judged at all.** The skill's own cost discipline
spends a critic on visual precisely because a builder's self-report is weakest
there, and that is the one instrument the run stopped buying.

So the honest answer to *is it progressing* is **not measurable right now**, and
that is a failure of the loop rather than a detail about it. A critic is running
as of this file's first commit.

**And there was no plan.** `plan.md` was generated once at wave 14 and never
consulted. Wave targets came from the previous wave's findings or from the
owner's own observations of a frame. The owner's observations were excellent
targets — the long lines, the flat green, the white slab were each a real defect
with a real cause — but *reacting to what the owner notices is not a route.*

## The three things that are true and unwelcome

**1. Visual 9 is not reachable with the bar as it stands.** Not expensive —
**unreachable.** The five Aljezur photographs are not on disk; `bar/bar.md` is
their written description. Three critics said independently that they can
falsify a frame against criteria stated *in words*, and would **refuse** to
write a verdict in the 6–8 band without pixels. The generic set lifted that
ceiling for texture statistics; it cannot lift it for *this place*. The
hyper-realism criterion is explicit that a render must sit beside a photograph
from the same viewpoint. **The unblock is five files in a directory, not a wave.**

**2. A large share of recent effort went to debt, not to the goal.** Four
separate findings of *derived, guarded, and never called* — foam, glitter,
diffraction, and a whole wave whose rows were never committed. That work was
necessary and it is why anything measures at all now. It also reads exactly like
standing still from outside, **because against the goal it is.**

**3. The physics is genuinely ahead of the picture, and that was the owner's own
ordering.** Cox & Munk retired as an input and returned as a limit; the seam,
the phase field, the terrace, the slope realisation, 562 suite rows. The
instruction was *eerst moet de wiskunde bewezen worden*. That half is close to
done. The picture is where the remaining distance is.

## The route

Each step states what must become **true**, not what someone should work on.
A step is finished when a measurement says so.

### Step 1 — restore the instrument (running now)
An independent critic re-scores all three lanes against the frozen bar **and**
the generic set's measurements. Until that lands, every claim of progress in
this run is self-assessment. **This is the only step that cannot be skipped**,
because every step below is prioritised by its output.

### Step 2 — the two structural blockers, both already named
- **Short-crestedness stops at the surf zone.** `free_surface` fades the
  directional realisation out over the last 60 m, so the picture's subject is a
  single-valued carrier phase, **long-crested by construction**. Coverage inside
  the surf zone is 0%. *(wave 19, running)*
- **One bar means one breaking line.** A Dean monotone ramp plus one Exner bar
  has exactly one `H/d` crossing, against the bar's three to four. *(wave 19,
  running)*

These two are one picture between them and they are the owner's own diagnosis:
*golven zijn geen lange lijnen, ze volgen de bodem.*

### Step 3 — the land, which two critics called the largest tell and neither owned
Wave 18 established the camera was standing on the landform and fixed it, ×164.
It also established what remains, with a measurement that rules out the obvious
routes: **97–99% of land pixels sample below half a bed cell**, so no
grid-resident field can vary across the near ground. **This needs a sub-grid
material, not a better bed** — and that is a different piece of work from
anything attempted so far.

### Step 4 — foam's last third
Correlation length and clot size are in bracket. **Lace and cusps are not**, and
the reason is exact: lace is foam persisting *after the water has gone*, which
needs a residence time different from the water's, and this model pins foam age
to the wave phase. Closing it means breaking that coupling.

### Step 5 — the frame the bar actually asks for
Every hero frame so far is a diagnostic. The hyper-realism criterion wants a
render from a viewpoint one of the owner's photographs was taken from. **Blocked
on step 0 below.**

### Step 0, which is not mine
**Put the five Aljezur photographs on disk**, in `gauntlet/sea/bar/`. Steps 1–4
proceed without them and are worth doing regardless. Step 5 and any visual score
above ~6 do not exist until this happens.

If the photographs are not going to be available, then the honest move is to
**change the target**: `visual = 6` against the written bar, with 9 reserved for
physics and prose. A target nobody can reach is not ambition — the skill's own
`bar-selection.md` says so, and a run that keeps a target it cannot buy will
report failure forever while doing good work.

## What changes in how the run is driven

1. **A critic every second wave on visual, minimum.** Self-reported scores are
   logged as `--tier screening` and never as a lifecycle verdict.
2. **`quote` and `status` re-read at every wave boundary**, and this file updated
   when a step closes — not left to rot as `plan.md` was.
3. **Waves are chosen from this route**, and when an owner observation redirects
   one, that gets written here as an amendment rather than silently replacing
   the plan that did not exist.

## Amendment, wave 19 — the third thing that breaks a crest up

Owner: *"Nabij de kust breken golven op. Je ziet in werkelijkheid nooit 1 lange
golf langs de kust."*

Step 2 named two mechanisms — short-crestedness faded out of the surf zone, and
one bar giving one breaking line. **There is a third, and it may dominate both.**

Suppose step 2 succeeds completely: crests short and groupy to the shoreline,
three or four bars to break over. If breaking is still applied as a
**deterministic threshold on a single carrier amplitude** — `H/d > γ` on one `H`
field — then every crest of the same height breaks at the same depth. The result
is **more parallel lines, not broken ones.**

What breaks a breaking line up is that **individual waves in a random sea have
different heights.** Rayleigh-distributed, so they break at different depths, at
different moments, at different places alongshore. The breaking "line" is a
scatter of segments whose envelope only resembles a line in a long exposure.

**That is Battjes & Janssen's own statement**, and it is why this is suspicious
rather than speculative: `Q_b` is *the fraction of waves breaking at a given
depth*, not *the wave breaks here*. The foam field is already built on `Q_b`.

So the question, put to the wave-field lane mid-round: **does the render draw
`E[breaking]`, or a realisation of which individual waves broke?** If it draws
the expectation, that is this run's dominant error class — mean where a
realisation belongs — at a level nobody has inspected: not the foam patch, not
the slope field, but **the wave population**. It would produce exactly the smooth
band the owner is describing.

If breaking turns out to already be a realisation over the height distribution,
that is a claim surviving a serious attempt to break it, and this project records
those as wins rather than passing over them.

## Amendment, wave 19 — the calm sea, and why it is a free falsification

Owner: *"Soms zijn er geen hoge golven, dan lijkt de zee net een meer. Maar dan
zie je zeker niet van die witte 'koppen'."*

**A limit case whose answer is known in advance** — ruling 14's shape, and the one
that has found every real defect in this run. Set the wind low and the swell low:
the frame must show **no whitecaps offshore at all**, while still showing
depth-limited breaking at the shore.

**It separates two whites the render may be conflating.** Open-water whitecapping
is **wind**-driven — steepness exceeding a limit, coverage rising steeply with
`U`. Surf-zone breaking is **depth**-limited, `H/d > γ`, and happens at any wind.
If the offshore white is driven by `Q_b` rather than by wind, a calm sea shows
foam where there should be none.

**And it has a sharp edge that the run has already half-recorded.** Section K's
own note says the whitecap literature spreads — *"3.41 quoted, 3.52 optimal, an
offset cubic in Callaghan et al. 2008"*. That difference is exactly the owner's
observation: **a pure power law never reaches zero**, it only becomes small; an
offset form has a **threshold wind speed below which coverage is identically
zero.** If the code carries the bare power law, it paints a little white on a
mirror-flat sea forever, and no amount of population work removes it.

**Why it is worth more than its cost.** It falsifies the whole foam path at the
cheap end of the parameter range, and it tests something the wave-population work
structurally cannot: the population decides *which* waves break and *how high*
they are, and it will not stop a wind-independent term from painting the calm
sea. The row must assert **exactly zero** offshore whitecap pixels, with a reach
integer — a row asserting "small" is the thirteenth way, a tolerance the size of
the thing it covers.
