# What this skill does not cover, and where it was read

**A register of known gaps and their closures.** Kept because a skill that knows its own boundary is
more useful than one that is merely silent at it — and because the way these were found is worth
keeping: each came from asking *"what kind of water is this?"* along an **axis** rather than from
listing subjects. Four of the six had the same shape, and it is the shape to look for next: **the
subject was present and the unifying axis was missing.**

**Status of this register.** Five of the six entries below are now **closed**: each has a chapter
section with its formulas, a reference implementation, a figure, and suite rows. The sixth is
**open and unsourced**, and is recorded as an admitted gap rather than given an invented citation.

Tiers follow [`12b`](12b-water-provenance.md)'s convention. Sources were web-verified 2026-08; the
skill's rule against citing what has not been read applies to this file as much as to any other.

| # | gap | status | where it lives now |
|---|---|---|---|
| 1 | Ice, optically | **closed** | [the phase axis](12-water-physics.md#the-phase-axis-ice-is-not-tinted-water-and-the-mechanism-differs-twice) · `reference-impl/ice.py` |
| 2 | The free jet in air | **closed** | [the Weber axis](12-water-physics.md#the-weber-axis-a-trickle-a-pistol-a-hose-and-a-fountain-are-one-jet) · `reference-impl/jet.py` |
| 3 | Water entry | **closed** | [the impulse axis](12-water-physics.md#the-impulse-axis-four-events-and-the-bright-one-is-not-the-first) · `reference-impl/impact.py` |
| 4 | Thin-film interference | **closed** | [the other phase axis](12-water-physics.md#the-other-phase-axis-thin-film-interference-and-this-chapters-own-trap-at-its-sharpest) · `reference-impl/thinfilm.py` |
| 5 | The hydraulic jump | **closed** | [travelling or standing](12-water-physics.md#travelling-or-standing-the-hydraulic-jump) · `reference-impl/openchannel.py` |
| 6 | Vortex structure | **open, unsourced** | nowhere — see below |

All five closures are guarded by [`validate_phases.py`](../reference-impl/validate_phases.py):
30 rows, 0 FAIL, and its `--bugs` harness proves 6 of 6 deliberate defects fire.

---

## 1 · Ice, and why it is not frozen water optically — **closed**

**Was:** one mention in the whole of both skills — *"ice = low roughness, high `F0`"* in a
snow-shading table. No lake ice, sea ice, glacier ice or icicles.

**Now:** the phase axis, with the mechanism separated from the interface. `n = 1.311` gives
`F0 = 0.01811` against water's 0.02048 — real and small — while the appearance is carried by
**scattering from bubbles and grain boundaries**, on Kubelka–Munk. The finding that made it worth a
section: at this chapter's own band points ice and water absorb *identically in green* (to 1.3%)
and differ by **3.96×** in blue, so the difference is a change of **shape** and no tint reproduces
a shape. Red:blue selectivity is **55.0 for ice against 25.6 for water** — 2.15× steeper. And
`R_∞` depends on `K/S` **alone**, so unlike clear water an ice slab's colour does not vanish as it
thins: *for water the colour is the path; for ice the colour is `K/S`.*

| | |
|---|---|
| `P` | Warren, S. G. & Brandt, R. E. (2008), *"Optical constants of ice from the ultraviolet to the microwave: A revised compilation"*, **J. Geophys. Res. Atmospheres 113**, D14220. DOI [10.1029/2007JD009744](https://doi.org/10.1029/2007JD009744). **The Pope & Fry of ice** — the `n`, `k` tabulation this skill builds on, exactly as it builds on Pope & Fry for water. |
| `P` | Warren, S. G. (2019), *"Optical properties of ice and snow"*, **Phil. Trans. R. Soc. A 377**:20180161. A review covering ice *and* snow together, which is the pairing this skill splits across two chapters. |

---

## 2 · The free jet in air, along its own axis — **closed**

**Was:** half-present, and it was the wrong half. The *submerged* jet was deep and guarded; the
breakup mechanism was derived in the waterfall cascade. What was missing was the **axis** that
makes a waterfall, a fountain, a fire hose and a water pistol one phenomenon.

**Now:** the aerodynamic Weber number and the four Lin & Reitz regimes, which sort six everyday
jets — trickle, water pistol, fog nozzle, garden hose, fountain, fire hose — into four regimes
**with no boundary moved to fit them**. The counter-intuitive consequence the axis exists to make
unavoidable: a fire hose's momentum makes its stream *less* coherent, not more. Two traps are named
and guarded: `We_g` is built on the **air's** density (using water's is an 829× error that puts
every jet past atomization), and `breakup_length_rayleigh` **returns NaN outside its own regime**
rather than reporting ~6000 diameters of intact column for a fire hose.

| | |
|---|---|
| `P` | Lin, S. P. & Reitz, R. D. (1998), *"Drop and spray formation from a liquid jet"*, **Annu. Rev. Fluid Mech. 30**, 85–105. The canonical review of the four regimes and their boundaries at `We_g` = 0.4 / 13 / 40.3. |
| `P` | Ohnesorge, W. (1936). The original regime diagram, `Oh` against `Re`. ⚠️ German-language original, **not opened here** — the *diagram* is cited, and every number comes from Lin & Reitz. |
| `P` | Rayleigh, Lord (1878). The most-unstable mode at `λ = 4.508·d`, which gives `D = 1.891·d` by volume conservation — the drops are nearly **twice** the jet's diameter. |

---

## 3 · Water entry: splash crown, cavity, Worthington jet — **closed**

**Was:** absent. The word "splash" appeared; the phenomenon did not.

**Now:** the impulse axis and its four-event schedule — crown, cavity, pinch-off, Worthington jet —
with the timing separated from the depth. The result a renderer needs: `t_p ~ √(d/g)` carries the
**body size** and not the impact speed, while `h_p ~ d·√Fr` carries the speed. Sweeping impact
speed at fixed size gives **three different exponents** — `U⁰` for the pinch-off time, `U^½` for
the jet speed, `U¹` for the depth — which is why tying the second flash to impact energy puts the
dependency on the wrong variable. A fifth of a second separates the two bright events for a thrown
rock, so the missing events were missing *visibly*.

⚠️ **One correction this section shipped and a suite row caught:** a Froude threshold alone is not
the cavity criterion. A 2.5 mm drip at 1 m/s has `Fr ≈ 41` and leaves no cavity, because at
millimetre scale surface tension closes it before hydrostatic pressure would. Both `Fr > 10` and
`We > 100` have to clear.

| | |
|---|---|
| `P` | Truscott, T. T., Epps, B. P. & Belden, J. (2014), *"Water Entry of Projectiles"*, **Annu. Rev. Fluid Mech. 46**, 355–378. The review: cavity formation, pinch-off, the sequence and the scalings. |
| `P` | Worthington, A. M. (1908), *A Study of Splashes*. The origin, and still the clearest photographic account of the sequence. |

---

## 4 · Thin-film interference: oil sheen and iridescence — **closed**

**Was:** absent as an optical mechanism. An oil slick appeared only as a *slick* — a
surface-tension film that damps capillary waves, which is a different effect and was covered. The
colour was not.

**Now:** the Airy summation, done in **amplitude** — which is the same interreflection geometric
series this chapter already sums for a pool's trapped light, with the one difference that matters,
since summing intensities loses the phase and gives a smooth colourless result. The chapter's own
trap is measured rather than warned about: three-sample RGB is 2.2% from the band-integrated truth
at one fringe across the visible band and **25.7% at two**, so the error grows **more than
tenfold** between them. ⚠️ And the Fresnel **sign** cannot be dropped here — it is a π phase shift,
and dropping it returns the complementary colour.

| | |
|---|---|
| `P` | Belcour, L. & Barla, P. (2017), *"A Practical Extension to Microfacet Theory for the Modeling of Varying Iridescence"*, **ACM TOG 36(4)** (SIGGRAPH). DOI [10.1145/3072959.3073620](https://doi.org/10.1145/3072959.3073620). Real-time-practical, works over a rough base layer, and **analytically pre-integrates the spectral response** so RGB and spectral renderers agree — precisely the aliasing measured here. This skill derives the underlying summation and measures the motivation; it does **not** reimplement their model. |

---

## 5 · The hydraulic jump, and standing structure in flow — **closed**

**Was:** absent. `Froude` appeared twice and the jump did not appear at all.

**Now:** the travelling/standing distinction, closed on Bélanger's conjugate depth. The two things
worth having: the closure has to be **momentum**, because a model that conserves energy across a
jump produces no jump and quietly returns the upstream depth — a silent, plausible failure, and
therefore a suite row; and the dissipation goes as the **cube** of the depth rise, so a factor of 7
in Froude number buys a factor of 10 000 in dissipated power. The power per unit width is handed to
the aerated-water sections as a **source term** rather than as a coverage, so white water in a
rapid comes out of the same covering-measure model as white water in surf.

| | |
|---|---|
| `P` | Bélanger, J.-B. — the momentum relation across the jump, giving the conjugate depth `h₂ = (h₁/2)·(−1 + √(1 + 8·Fr₁²))` with `Fr₁ = U₁/√(g·h₁)`. |

⚠️ **The limitation travels with every number:** Bélanger neglects bed roughness, and a rapid is the
roughest bed there is — so it gives the **geometry** of the jump and **overstates the energy that
survives it**.

---

## 6 · Vortex structure: eddies, whirlpools, drain vortices — **open, and unsourced**

**Status: absent, and no verified anchor.** Zero mentions in either skill.

⚠️ **This entry has no reference because none was found and checked.** The other five carry one
because one was verified; inventing a plausible citation to make the table symmetric is exactly
what [`12b`](12b-water-provenance.md)'s convention forbids. The eddy behind a boulder, the shed
vortex street, the bathtub vortex and the whirlpool are real, common, and currently outside
everything here.

**What closing it would need**, stated so the next pass has a target rather than a topic: a
circulation-carrying description that survives being sampled on a surface — the surface signature
of a vertical vortex (the depression profile and the spiral of surface debris), the shedding
frequency behind an obstacle as a Strouhal number, and the question this skill would have to answer
before writing anything, which is whether a vortex belongs in the **flow field** the river sections
already assume or in the **surface** they render. Until a source is opened, nothing above this
paragraph is asserted.

---

## The pattern, kept because it predicted

Four of these six were found by the same question, and all four had the same shape: **the subject
was present and the axis was missing.** Snow was covered and ice was not, because the phase axis
was never drawn. Waterfalls were derived and hoses were not, because the Weber axis was never
drawn. Splashes were named and their sequence was not, because the impulse axis was never drawn.
Rapids were absent because nothing separated structure that travels from structure that stands.

So the next place to look is not another subject. It is another **axis**: phase, confinement scale,
energy input, composition, and whether the structure travels or stands. That search closed five
gaps in one pass, and the one it did not close is the one where an axis was found and a **source**
was not — which is the honest place for a register to stop.
