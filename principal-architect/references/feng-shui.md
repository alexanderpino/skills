# Feng shui — placement & flow in inhabited structures

A structure is *inhabited* when people move through it repeatedly and their
effectiveness depends on how it is arranged. A building is one such structure. So is
a codebase (inhabited by the engineer who arrives in six months), a screen (inhabited
by the end user), and this skill's own docs tree (inhabited by the next agent). Feng
shui's **form school** is the oldest surviving body of heuristics about arranging
inhabited space — where to place things, how movement should flow, what accumulation
does to a space — and those heuristics transfer to the newer structures because they
are about *human response to arrangement*, not about buildings.

This file states the transferable principles once (§1), then applies them to the
three spaces this skill touches: the codebase (§3), the screen (§4) — which also
closes the skill's UI/interaction gap — and the docs tree (§5). §6 confines the
vocabulary so it never leaks into produced artifacts.

**This is not a foreign philosophy bolted on — it names the one already underneath.**
Modern software and requirements maxims keep independently rediscovering the form
school, which is itself the evidence that the heuristics track something stable in
the *inhabitants* rather than in any era's structures. The rediscoveries, with the
shared invariant each pair converged on:

| Modern maxim | Form-school principle | The shared invariant |
|---|---|---|
| **YAGNI** | declutter — its prospective half | possessions in proportion to *present* use: declutter removes what no longer serves; YAGNI declines what doesn't yet |
| **KISS** | declutter, applied to the design itself | ornament in the structure blocks flow exactly as objects in the room do |
| **SRP** (the S of SOLID) | one room, one purpose | mixed purpose taxes every occupant — a bed in the office *is* mixed responsibility (= cohesion/CCP, `structure.md` §2) |
| **DIP** (the D), SDP | backing | depend on the stable; face the volatile knowingly (§1.6) |
| **MoSCoW** (DSDM/BABOK prioritisation) | balance | attention in proportion to purpose: Musts take the commanding position of a release; Won'ts are clutter declined in advance |
| this skill's *"documentation must earn its keep"* | declutter | every artifact pays attention-rent |
| *conceptual integrity*; ubiquitous language | balance; one voice per room | one coherent style per inhabited space |
| the README manifest ("two reads instead of twenty") | one clear mouth | a legible entrance orients every arrival |

And an honest negative result, because forcing a map would be the very clutter the
lens warns against: **O, L, and I of SOLID do not survive the transfer** — Liskov
substitutability has no spatial analogue. That agrees, independently, with
`structure.md` §2's own verdict that SOLID's architectural payload is DIP alone;
where the lens and the standards refuse the same correspondence, both are probably
right.

**Epistemic status — read this first.** Feng shui has two halves. The **form school**
(*luan tou*) is empirical vernacular: observations about approach, sightlines,
backing, blockage, and accumulation, refined over centuries of watching people occupy
structures. The **compass school** (*li qi* — cardinal directions, birth charts,
flying stars) depends on a literal orientation on the earth and does **not**
transfer; nothing below uses it. And the form school is used here as a *checklist
generator, not an authority*: every principle in §1 is independently corroborated by
a named modern source (§7), and it is always the modern source — not feng shui — that
you cite in a produced document (§6). If a principle and the evidence ever disagree,
the evidence wins; the lens is a way of *noticing*, never a way of *justifying*.

**This transfer has a precedent.** Christopher Alexander — a building architect —
codified what makes inhabited space work as named, reusable configurations
(*A Pattern Language*, 1977; *The Timeless Way of Building*, 1979). The Gang of Four
ported that structure into software wholesale and cite him in *Design Patterns*
(1994). The software profession's entire pattern vocabulary is already a port of
spatial-arrangement thinking into a medium its originators never saw. This file makes
the same move from an older source, and holds it to the same standard: a principle
earns its place only when it maps to something independently verified.

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

The lens lands on machinery this skill already has — it adds a way of *noticing*, not
new rules. Walk a codebase the way a form-school practitioner walks a site: enter
where a newcomer enters, follow the paths a change would take, watch where things
pile up.

- **Commanding position + backing** *is* the Dependency Rule (`structure.md` §2): the
  domain core is the occupant, ports give it sight of everything that enters,
  adapters keep it out of the traffic, and SDP — depend in the direction of
  stability — is literally "the mountain behind." A core that imports a volatile
  framework is a desk with its back to a window.
- **One clear mouth** — per bounded context, the Open Host Service / published
  language (`structure.md` §1, `interfaces.md`). A context reachable by three ad-hoc
  routes has no mouth, and every route will be depended on.
- **Poison arrow** — a dependency that bypasses the published interface to strike at
  internals: reaching into another context's tables, importing a private module
  across a boundary, a "temporary" direct call around the gateway. This is the
  data-ownership smell of `data-architecture.md` and ADP/boundary violations of
  `structure.md` §2, seen as a line you could draw on the context map.
- **Blocked flow** — the god object / mega-service every request funnels through
  (a blocked doorway), and its inverse, the *rushing corridor*: a pass-through layer
  that touches everything and transforms nothing, pure ceremony in every path.
- **Clutter** — dead code, near-duplicate names for different things, stale feature
  flags, abstractions built for a future that never came. Feng shui's claim is the
  sharp one: accumulation isn't neutral storage, it *costs* — every reader pays
  attention-rent to what no longer serves.
- **Balance** — fan-in/fan-out and size metrics (`methods.md` §9) read as
  proportion: a 40-file module beside six one-file neighbours is an over-stuffed
  room next to empty ones, and usually a boundary drawn in the wrong place.

What to do on a hit is unchanged: name the finding in standard vocabulary, record it
in the SD/HLD "known issues / debt" section with the quality attribute it threatens
(`significance.md`), and let a deliberate ADR — including "we accept this for now" —
be the outcome. The lens only makes the walk-through systematic: seven questions,
asked of every space you enter.

---

## 4. The screen as a space — UI & interaction

Software architecture and UI didn't exist when these principles were formed, but a
screen is an inhabited space in exactly the form-school sense: it has an entrance
(where the eye lands), paths (task flows), a commanding position (where the primary
action sits), and clutter. This section is the skill's home for reasoning about
interaction arrangement — a gap nothing else in the skill covers.

**Where it lands in the artifact set.** UI quality is **not** a new document type.
The quality is an **Interaction capability** driver — ISO/IEC 25010:2023's
characteristic (formerly Usability; sub-characteristics in `standards.md`) — written
as a measured `Q.xx` scenario in the PRD like any other quality. The *arrangement*
that meets it is design content in the SD for that screen or feature (views, states,
flows), chosen and traded like any tactic. A deliberate interaction-structure choice
that is costly to reverse — a navigation paradigm, a disclosure strategy, dropping a
platform convention — passes the `significance.md` test and gets an ADR.

**The sub-characteristics, read spatially.** Each ISO 25010 Interaction capability
sub-characteristic is one of §1's questions asked of a screen:

| 25010 sub-characteristic | The spatial question |
|---|---|
| Appropriateness recognizability | can you tell what the room is for from the doorway? |
| Learnability | are things where the occupant's experience says they'll be? |
| Operability | is the primary action in the commanding position — visible, reachable, out of the clutter? |
| User-error protection | is the dangerous door out of the walkway, marked, and reversible? |
| Self-descriptiveness | does the space explain itself as you move, or need a guide? |
| User engagement | is the room balanced — inviting rather than crowded or bare? |
| Inclusivity | is there more than one way in and through (input modes, assistive tech)? |

**The tactics** (the §3-of-`structure.md` "supply side," for this quality): visual
hierarchy (weight ∝ importance) · progressive disclosure (declutter in time, not
just space) · consistent placement & platform convention (backing) · large, near
targets for frequent actions (Fitts's law — the quantitative form of "commanding
position") · grouping by proximity and common region (Gestalt — walls make rooms) ·
safe defaults, confirmation + undo for destructive actions (no poison arrows) ·
one primary action per screen (one mouth). Each buys interaction quality at a cost —
disclosure hides, convention constrains, confirmation slows — so record the trade
like any tactic.

**A worked `Q.xx`**, in the 6-part scenario form (`methods.md` §7):

> **Q.07 — Interaction capability (operability, learnability).** A first-time user
> (*source*) attempting the primary task (*stimulus*) on the main screen under
> normal load (*environment*) of the web UI (*artifact*) completes it unaided
> (*response*) within 3 interactions and 60 seconds, primary action visible without
> scrolling at supported viewports (*response measure*). Verified by moderated
> usability test (5 users) and the production analytics funnel.

Grounding for this section is modern and testable — ISO 9241-110's interaction
principles, Gestalt grouping, Fitts (1954), Nielsen's heuristics (§7). The feng shui
framing adds the discipline of *walking the screen as a space*: enter where the eye
enters, follow the task path, note what blocks it and what has accumulated.

---

## 5. The docs tree as a space

`repository-structure.md` is already a form-school document — it just doesn't use the
words: one clear mouth (the README manifest — "an agent loads one file to learn the
whole map"), one concept per room with a stable name (ADR/SD/driver IDs), sight
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
corroborates every item you act on.

| Claim (this file) | Corroborated by | Body / author |
|---|---|---|
| Form-school principles (§1) | vernacular tradition, used descriptively — never cited as authority | — |
| Spatial patterns → software patterns is a valid transfer | *A Pattern Language*; *The Timeless Way of Building*; cited in *Design Patterns* (1994) | Christopher Alexander; Gamma, Helm, Johnson & Vlissides |
| Commanding position / backing → dependency direction (§3) | Dependency Rule; SDP/ADP component principles | Robert C. Martin (see `structure.md` §2) |
| One mouth per context (§3) | Open Host Service, Published Language | Evans; The Open Group O-AA (see `structure.md` §1) |
| Poison arrow = ownership/boundary violation (§3) | data ownership & context boundaries | `data-architecture.md`; Evans |
| Clutter costs the reader (§3) | dead code / duplicate-name smells | `methods.md` §9; Fowler, *Refactoring* |
| UI quality is a named, measurable characteristic (§4) | **ISO/IEC 25010:2023** Interaction capability | ISO/IEC |
| Interaction principles (§4) | **ISO 9241-110:2020** (self-descriptiveness, conformity with expectations, error robustness) | ISO |
| Commanding position on screen, quantified (§4) | Fitts's law (1954); visibility & hierarchy heuristics | Fitts; Nielsen (10 usability heuristics) |
| Grouping = walls make rooms (§4) | Gestalt principles (proximity, common region) | Wertheimer; Palmer |
| Docs tree navigability (§5) | the RAG-optimisation rationale | `repository-structure.md` |
| Rediscovery table (intro) — YAGNI; KISS; SRP/DIP; MoSCoW | Extreme Programming; the Lockheed design maxim; *Agile Software Development*; DSDM / BABOK prioritisation | Beck & Jeffries; Kelly Johnson; Robert C. Martin; Dai Clegg (DSDM Consortium) |

When any of this disagrees with the org's mandated standard or house style, conform
to theirs (the skill's standing rule) — this lens least of all is worth a divergence.
