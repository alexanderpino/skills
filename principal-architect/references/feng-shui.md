# Feng shui — placement & flow in inhabited structures

A structure is *inhabited* when people move through it repeatedly and their
effectiveness depends on how it is arranged. A building is one; so is a codebase
(inhabited by the engineer who arrives in six months), a screen (by the end user),
and this skill's docs tree (by the next agent). Feng shui's **form school** is a
long-lived body of vernacular heuristics about arranging inhabited space — where to
place things, how movement should flow, what accumulation does to a space. This file
reduces its transferable principles to corroborated invariants (§1), applies them to
the three spaces this skill touches — the codebase (§3), the screen (§4, the skill's
home for interaction-arrangement guidance), the docs tree (§5) — and confines the
vocabulary so it never leaks into produced artifacts (§6).

**Epistemic status — the contract for everything below.** Feng shui has two halves.
The **form school** (*luan tou*) deals in approach, sightlines, backing, blockage,
and accumulation. The **compass school** (*li qi* — cardinal directions, birth
charts, flying stars) depends on a literal orientation on the earth and does **not**
transfer; nothing below uses it. And the form school itself is a vernacular
tradition, not a body of evidence — it carries plenty that stays behind too (dragon
veins, fortune). So the rule for this file: a principle appears only as an invariant
that a named modern source corroborates (§7), and it is always that source — never
feng shui — that you cite in a produced document (§6). The lens is a *checklist
generator, not an authority*: a way of noticing, never a way of justifying. Where a
principle and the evidence disagree, the evidence wins.

**The precedent.** Christopher Alexander — a building architect — codified what makes
inhabited space work as a *pattern language*: named, composable problem-in-context /
resolution pairs (*A Pattern Language*, 1977; *The Timeless Way of Building*, 1979).
The Gang of Four adopted that format for software and cite him in *Design Patterns*
(1994) — while noting their patterns are not his. What transferred there was the
**method** of capturing arrangement knowledge, not the arrangements themselves
(nothing about Observer is spatial). This file attempts the narrower, riskier
transfer — content, not just format — riskier in kind, which is exactly why it is
bound to the corroboration contract above.

**Convergences, not rediscoveries.** Several modern maxims, and this skill's own
standing rules, reduce to the same invariants as §1's principles. The mappings are
constructed here, after the fact — Beck was not reading feng shui — so they prove
nothing by themselves; the named sources in §7 carry all the authority. What the
convergence buys is cheaper and still real: confidence that §1's questions are worth
asking of structures the form school never saw, because practitioners of those
structures keep arriving at the same answers.

| Modern maxim / rule | Form-school principle | The shared invariant |
|---|---|---|
| **YAGNI** | declutter — its prospective half | possessions in proportion to *present* use: declutter removes what no longer serves; YAGNI declines what doesn't yet |
| **KISS** | declutter, applied to the design itself | ornament in the structure blocks flow much as objects in the room do |
| **SRP** (the S of SOLID) | one room, one purpose | mixed purpose taxes every occupant — a bed in the office *is* mixed responsibility (= cohesion/CCP, `structure.md` §2) |
| **DIP** (the D), SDP | backing | depend on the stable; face the volatile knowingly (§1.6) |
| **MoSCoW** prioritisation | balance | attention in proportion to purpose: Musts take the commanding position of a release; Won'ts are clutter declined in advance |
| this skill's *"documentation must earn its keep"* | declutter | every artifact pays attention-rent |
| *conceptual integrity*; ubiquitous language | balance; one voice per room | one coherent style per inhabited space |
| the README manifest ("two reads instead of twenty") | one clear mouth | a legible entrance orients every arrival |

And a negative result, held to the same honesty: **O, L, and I of SOLID have no
spatial analogue** — Liskov substitutability is about types, not placement — and
forcing a map would be the very clutter the lens warns against. That sits
consistently with where `structure.md` §2 already draws the altitude line: SOLID's
architectural payload there is *DIP → the Dependency Rule plus the component
principles* — dependency direction and cohesion, exactly the two parts that map here
(backing; one room, one purpose) — while O, L, and I stay at code altitude in both
files.

---

## 1. The principles (stated once)

Seven form-school principles, each reduced to the invariant that survives the
transfer. The invariant is what you apply; the feng shui name is the mnemonic that
makes it stick.

1. **Commanding position.** The occupant sits where they can see the entrance
   without being in the traffic through it, with solid backing behind.
   *Invariant: the controlling element has visibility over what enters, without
   itself being a chokepoint, and rests on something stable.*
2. **One clear mouth.** A space is entered through a deliberate, legible entrance
   (the "mouth of qi"); a visitor should never wonder how to get in.
   *Invariant: every space has one obvious way in that orients you on arrival.*
3. **Unblocked, unhurried flow.** Movement through the space neither stagnates in
   dead ends nor rushes straight through (the "rushing corridor" where front door
   aligns with back door and everything shoots past unused).
   *Invariant: paths through the structure neither bottleneck nor bypass.*
4. **No poison arrows.** No sharp edge points at where someone sits; harsh direct
   lines are softened or redirected.
   *Invariant: nothing pierces a boundary to strike directly at an interior.*
5. **Declutter.** Accumulated unused objects block flow and attention; what no
   longer serves the space is removed from it.
   *Invariant: remove what is no longer used; accumulation is a cost, not a neutral.*
6. **Backing.** Sit with the mountain behind and the open view in front — support
   from the stable, exposure only toward what you face deliberately.
   *Invariant: depend on the stable; face the volatile knowingly.*
7. **Balance.** No area of the space is over-weighted or abandoned; use is
   distributed in proportion to purpose (yin–yang as complement, not symmetry).
   *Invariant: distribute mass and attention in proportion to use.*

## 2. One lens, three spaces

The same seven questions, asked of each structure. Each software/screen cell names
the standard concept it corresponds to — the lens finds the issue; the standard
concept names it in the doc.

| Principle | Building | Codebase | Screen |
|---|---|---|---|
| Commanding position | desk facing the door, out of its path | domain core sees every input through a port; a destination, never a thoroughfare | primary action visible on arrival, prominent, not buried in traffic |
| One clear mouth | a legible front door | index/README manifest; `AD.md`; one published entry point per context | one obvious starting point per screen; legible navigation |
| Unblocked flow | no dead-end rooms, no shoot-through corridor | no chokepoint component; no layer everything tunnels *past* | task flow without dead ends; no forced detour through the irrelevant |
| No poison arrows | no knife-edge aimed at the bed | no dependency that pierces a boundary to reach internals | no destructive control aimed at the resting cursor |
| Declutter | remove what's unused | dead code, abandoned abstractions, stale flags — deleted | every element earns its pixels; progressive disclosure |
| Backing | solid wall behind the desk | depend toward stability (SDP); volatile at the edges | rely on established conventions; novelty only where it pays |
| Balance | no over-stuffed room beside an empty one | no god module beside anaemic ones; size ∝ responsibility | visual weight ∝ importance; whitespace is load-bearing |

---

## 3. The codebase as a space

Walk a codebase the way a form-school practitioner walks a site: enter where a
newcomer enters (the README, the index, the published interface), follow the paths a
change would take, and watch where things pile up. The §2 matrix gives the
correspondences; what this section adds is the judgment calls the matrix can't carry,
and what to do on a hit.

- **Hub or chokepoint?** The commanding position and the blocked doorway can look
  alike — both have high fan-in. Two tests separate them. *Terminate vs transit:*
  does traffic arrive through defined ports and get **answered** there (a healthy
  core is a destination), or does it pass **through** on the way to somewhere else
  (pass-through coupling)? *Cohesion:* does it hold one purpose (CCP,
  `structure.md` §2), or accrete logic that belongs to its callers? A hexagonal
  domain core passes both; a god object fails both; a layer that touches everything
  and transforms nothing fails the first — that is the rushing corridor.
- **Poison arrows** are lines you could draw on the context map: reaching into
  another context's tables, importing a private module across a boundary, a
  "temporary" call around the gateway (`data-architecture.md` ownership;
  ADP/boundary rules, `structure.md` §2).
- **Clutter** is the sharp claim worth importing: dead code, stale feature flags,
  near-duplicate names, abstractions built for a future that never came are not
  neutral storage — every reader pays attention-rent to what no longer serves.
- **Balance** reads fan-in/out and size metrics (`methods.md` §9) as proportion: a
  40-file module beside six one-file neighbours is usually a boundary drawn in the
  wrong place.

On a hit, the procedure is the skill's existing one, unchanged: name the finding in
standard vocabulary, record it in the SD/HLD "known issues / debt" section with the
quality attribute it threatens (`significance.md`), and let a deliberate ADR —
including "we accept this for now" — be the outcome.

**A worked walk (one trial — evidence, not proof).** The lens was exercised once
against a real ~8,600-line, 42-module Python codebase: two independent reviewers,
same output contract (verified findings with file:line evidence, standard
vocabulary), one walking with §§1–3, the other with the `methods.md` §9 smell list
and dependency-graph metrics. They **converged** on the major duplications, the
flat-namespace problem, and — a good sign for both — identical clean checks (no
cycles, healthy high-fan-in hubs, no dead code). Each also found real, code-verified
issues the other missed. Lens-unique finds map exactly to the questions the smell
list has no category for: *poison arrows* surfaced five modules consuming another
module's underscore-private helpers as their de facto API (13+ call sites); *backing*
surfaced a published output depending on the module its own README calls a
throwaway sandbox (a stability inversion, SDP); *one clear mouth* surfaced manifest
drift — a README section reading "two files, both deliberately small" above three
bullets, the first a 513-line module. Baseline-unique finds were metric-shaped: an
exhaustive count of a helper duplicated seven times, and a 568-line mega-module the
lens walk *missed*. The honest conclusion from n=1: the seven questions and the
smell list cover **complementary failure classes** — boundary piercing, stability
direction, and entrance legibility on one side; exhaustive counting and bulk on the
other. Walk with both, which is why this file sits beside `methods.md` §9 rather
than replacing it.

---

## 4. The screen as a space — UI & interaction

A screen is an inhabited space in exactly the form-school sense: an entrance (where
the eye lands), paths (task flows), a commanding position (where the primary action
sits), and clutter. The skill already *names* interaction quality — **ISO/IEC
25010:2023 Interaction capability** (`standards.md`) — and can already derive
measured scenarios for it (`methods.md` §7). What nothing else covers is how to
reason about the **arrangement** that meets those scenarios; that lives here.

**Where it lands in the artifact set.** No new document type. The quality is a
`Q.xx` driver in the PRD, written as a 6-part scenario like any other; the
arrangement that meets it is design content in the SD for that screen or feature;
and an interaction-structure choice that is costly to reverse — a navigation
paradigm, a disclosure strategy, dropping a platform convention — passes the
`significance.md` test and gets an ADR. The *architectural* end of interaction
quality (separating the UI concern, supporting undo/cancel, maintaining task and
user models) lives in `structure.md` §3's tactic table; the screen-level tactics
below are design-altitude and deliberately stay out of it.

**The eight sub-characteristics, read spatially** (ISO 25010:2023; names per
`standards.md`):

| 25010 sub-characteristic | The spatial question |
|---|---|
| Appropriateness recognizability | can you tell what the room is for from the doorway? |
| Learnability | are things where the occupant's experience says they'll be? |
| Operability | is the primary action in the commanding position — visible, reachable, out of the clutter? |
| User-error protection | is the dangerous door out of the walkway, marked, and reversible? |
| Self-descriptiveness | does the space explain itself as you move, or need a guide? |
| User engagement | is the room balanced — inviting rather than crowded or bare? |
| Inclusivity | does the room serve occupants of every background — ages, cultures, languages, circumstances? |
| User assistance | can occupants with the widest range of abilities move through the room — alternate doors, ramps, rails (input modes, assistive tech)? |

**Screen-level tactics** (each buys interaction quality at a cost — disclosure
hides, convention constrains, confirmation slows — so record the trade like any
tactic): visual hierarchy (weight ∝ importance) · progressive disclosure (declutter
in time, not just space) · consistent placement & platform convention (backing) ·
large, near targets for frequent actions (Fitts's law — the quantitative form of
"commanding position") · grouping by proximity and common region (Gestalt — walls
make rooms) · safe defaults, confirmation + undo for destructive actions (no poison
arrows) · one primary action per screen (one mouth) · contextual help at the point
of need (self-descriptiveness, learnability) · operable by keyboard, assistive
tech, and alternate inputs (user assistance).

**A worked `Q.xx`**, in the 6-part scenario form (`methods.md` §7):

> **Q.07 — Interaction capability (operability, learnability).** A first-time user
> (*source*) attempting the primary task (*stimulus*) on first visit, with no
> onboarding, at a default supported viewport (*environment*), in the web UI
> (*artifact*), completes it unaided (*response*) within 3 interactions and 60
> seconds, primary action visible without scrolling (*response measure*). Verified
> by moderated usability test (5 users) and the production analytics funnel.

Grounding for this section is modern and testable — ISO 9241-110:2020
(self-descriptiveness, conformity with user expectations, and use-error robustness
are three of its seven interaction principles), Gestalt grouping, Fitts (1954),
Nielsen's heuristics (§7). The lens adds the walk-through discipline: enter where
the eye enters, follow the task path, note what blocks it and what has accumulated.

---

## 5. The docs tree as a space

`repository-structure.md` is already a form-school document — it just doesn't use
the words: one clear mouth (the README manifest — "an agent loads one file to learn
the whole map"), one concept per room with a stable name (ADR/SD/driver IDs), sight
lines from the inside back out (`ARCH-REF:` markers), no clutter by construction
(triage — "documentation must earn its keep"), and append-only decisions so no room
silently changes purpose. Nothing to add there; but when you *extend* the tree, ask
§1's questions of the extension: does the new doc have an obvious way in from the
manifest, does anything now have two competing entrances, is anything accumulating
that the triage table says shouldn't exist?

---

## 6. Vocabulary containment — where these words may appear

The lens is for **diagnosis**; produced artifacts speak the skill's standard
language. In an ADR, HLD, SD, or PRD, the finding is "a cyclic dependency between X
and Y (threatens maintainability)," never "a poison arrow"; the citation is SDP, ISO
25010, or Fitts, never feng shui. Two reasons: the org's readers share the standard
vocabulary and not this one (`house-style.md` — conform outward), and the standards
are the actual authority (§ *epistemic status*). The mnemonic names live in your
head, in review conversation if the team enjoys them, and in this file.

**The one literal exception:** when the entity of interest *is* a physical space —
an office, retail floor, data-centre layout — feng shui may be a genuine stakeholder
concern (a client, market, or cultural requirement). Then it stops being a lens and
becomes elicitable domain content: capture it like any concern (`methods.md` §5),
with the stakeholder who holds it named, and requirements written verifiably
(ISO/IEC/IEEE 29148) — never fabricated on the stakeholder's behalf.

---

## 7. Grounding

Same rule as `structure.md`: the lens generates the checklist; a named modern source
corroborates every item you act on. Claims *about* the tradition itself are kept
descriptive and minimal — this file asserts no history it cannot source.

| Claim (this file) | Corroborated by | Body / author |
|---|---|---|
| Form-school principles (§1) | vernacular tradition, used descriptively — never cited as authority | — |
| Pattern-language *format* transfers to software | *A Pattern Language*; *The Timeless Way of Building*; adopted and cited in *Design Patterns* (1994) | Christopher Alexander; Gamma, Helm, Johnson & Vlissides |
| Commanding position / backing → dependency direction (§3) | Dependency Rule; SDP/ADP component principles | Robert C. Martin (see `structure.md` §2) |
| One mouth per context (§3) | Open Host Service, Published Language | Evans; The Open Group O-AA (see `structure.md` §1) |
| Poison arrow = ownership/boundary violation (§3) | data ownership & context boundaries | `data-architecture.md`; Evans |
| Clutter costs the reader (§3) | dead code / duplicate-name smells | `methods.md` §9; Fowler, *Refactoring* |
| UI quality is a named, measurable characteristic; 8 sub-characteristics (§4) | **ISO/IEC 25010:2023** Interaction capability | ISO/IEC |
| Interaction principles (§4) | **ISO 9241-110:2020** (7 principles; three named in §4) | ISO |
| Commanding position on screen, quantified (§4) | Fitts's law (1954); visibility & hierarchy heuristics | Fitts; Nielsen (10 usability heuristics) |
| Grouping = walls make rooms (§4) | Gestalt principles (proximity, common region) | Wertheimer; Palmer |
| Docs tree navigability (§5) | the RAG-optimisation rationale | `repository-structure.md` |
| Convergence table (intro) — YAGNI; KISS; SRP/DIP; MoSCoW | Extreme Programming; the Lockheed design maxim; *Agile Software Development*; MoSCoW (devised at Oracle, adopted by DSDM) | Beck & Jeffries; Kelly Johnson; Robert C. Martin; Dai Clegg |

When any of this disagrees with the org's mandated standard or house style, conform
to theirs (the skill's standing rule) — this lens least of all is worth a divergence.
