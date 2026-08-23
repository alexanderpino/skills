# What this skill does not cover, and where to read it

**A register of known gaps, each with a verified primary source.** Recorded because a skill that
knows its own boundary is more useful than one that is merely silent at it — and because the way
these were found is worth keeping: each came from asking *"what kind of water is this?"* along an
axis rather than listing subjects. Two of them are the same shape, and it is the shape to look for
next: **the subject was present and the unifying axis was missing.**

⚠️ **Nothing here is covered yet.** Every entry is a gap with a reading anchor, not a summary of
material that exists elsewhere in the skill. Tiers follow `12b`'s convention. Sources below were
web-verified 2026-08; the skill's rule against citing what has not been checked applies to this file
as much as to any other.

---

## 1 · Ice, and why it is not frozen water optically

**Status: absent.** One mention in the whole of both skills — *"ice = low roughness, high F0"* in a
snow-shading table. No lake ice, sea ice, glacier ice or icicles.

**Why it matters here.** The generation side already builds the landform: `terrain-architect`'s
glacial chapter carries the morphology. Nothing says how to draw the result. And ice is **not** a
tint on water: `n ≈ 1.31`, but its appearance is dominated by **scattering from air inclusions,
bubbles and grain boundaries**, not by absorption along a path. Glacier ice is blue for a different
reason than deep water is blue — the blue absorption is *weak*, so blue survives many scattering
events and returns, while red is removed. Rendering ice as "transparent water with a blue tint" is
the `waterColor` category error of chapter `12` wearing a different coat.

| | |
|---|---|
| `P` | Warren, S. G. & Brandt, R. E. (2008), *"Optical constants of ice from the ultraviolet to the microwave: A revised compilation"*, **J. Geophys. Res. Atmospheres 113**, D14220. DOI [10.1029/2007JD009744](https://doi.org/10.1029/2007JD009744). **The Pope & Fry of ice** — the tabulated absorption this skill would build on, exactly as it builds on Pope & Fry for water. Note its own finding: blue and near-UV absorption is *weaker* than earlier compilations said. |
| `P` | Warren, S. G. (2019), *"Optical properties of ice and snow"*, **Phil. Trans. R. Soc. A 377**:20180161. A review covering ice *and* snow together, which is the pairing this skill splits across two chapters. |

**What a first section would have to establish:** the scattering-dominated regime and why the
path-length doctrine does not transfer unchanged; ice over water as a layered medium; and the
bubble-density axis that separates clear lake ice from white glacier ice — the same
covering-measure reasoning the foam section already owns.

---

## 2 · The free jet in air, along its own axis

**Status: half-present, and it is the wrong half.** The **submerged** jet is deep and guarded — the
pool's return jet, its boil, the round-jet constants, the eikonal capillary-gravity wake. The
breakup *mechanism* is derived too, in the waterfall cascade: sheet → perforated sheet → ligaments
→ droplets, by **Rayleigh–Plateau**, most-unstable mode ≈ 9× the column radius.

**What is missing is the axis.** A waterfall, a fountain, a fire hose and a water pistol are **one
phenomenon at different Weber numbers**, and the skill derives the endpoint without the parameter
that orders them. The consequence is counter-intuitive and worth having: a fire hose's momentum
makes its stream *less* coherent, not more.

| | |
|---|---|
| `P` | Lin, S. P. & Reitz, R. D. (1998), *"Drop and spray formation from a liquid jet"*, **Annu. Rev. Fluid Mech. 30**, 85–105. The canonical review of the four regimes — Rayleigh, first wind-induced, second wind-induced, atomization — and their boundaries. |
| `P` | Ohnesorge, W. (1936). The original regime diagram, `Oh` against `Re`; the classification everything since is a refinement of. ⚠️ German-language original, not opened here — cite the *diagram*, and take numbers from Lin & Reitz. |

**The seed relations, all closed form and therefore suite-able:**
`We = ρ U² d / σ` · `Oh = μ / √(ρ σ d)` · `Oh = √We / Re` · breakup length against `We`.

---

## 3 · Water entry: splash crown, cavity, Worthington jet

**Status: absent.** The word "splash" appears; the phenomenon does not. This is everything that
*falls into* water — a rock, a body, a projectile, and at the small end every raindrop on every
puddle.

**Why it matters.** It is the most common water event in a game after waves, and it has structure
that a particle burst cannot fake: an ejecta **crown** rising at impact, an **air cavity** dragged
down behind the body, a **pinch-off** when the cavity collapses under hydrostatic pressure, and the
**Worthington jet** that fires upward out of that collapse — often *higher* than the splash that
preceded it, and delayed from it. The delay is the tell: a renderer that emits one particle burst at
contact has drawn the first event and skipped the two that follow.

| | |
|---|---|
| `P` | Truscott, T. T., Epps, B. P. & Belden, J. (2014), *"Water Entry of Projectiles"*, **Annu. Rev. Fluid Mech. 46**, 355–378. The review: cavity formation, pinch-off, the sequence and the scalings, including the effect of surface coating and spin. |
| `P` | Worthington, A. M. (1908), *A Study of Splashes*. The origin, and still the clearest photographic account of the sequence. |

---

## 4 · Thin-film interference: oil sheen and iridescence

**Status: absent as an optical mechanism.** An oil slick appears in this skill only as a *slick* —
a surface-tension film that damps capillary waves, which is a different physical effect entirely
and is covered. The **colour** is not.

**Why it belongs here rather than in a general material chapter.** It is one of the few water
appearances driven by **interference** rather than by absorption, scattering or Fresnel, so none of
this chapter's machinery reaches it. And it lands directly on a trap the skill already names:
thin-film colour is a *spectral* phenomenon, so evaluating it in RGB aliases — which is
[a channel is a band, not a wavelength](12-water-physics.md#a-channel-is-a-band-not-a-wavelength)
in its sharpest form.

| | |
|---|---|
| `P` | Belcour, L. & Barla, P. (2017), *"A Practical Extension to Microfacet Theory for the Modeling of Varying Iridescence"*, **ACM TOG 36(4)** (SIGGRAPH). DOI [10.1145/3072959.3073620](https://doi.org/10.1145/3072959.3073620). Real-time-practical, works over a rough base layer, and **analytically pre-integrates the spectral response** so RGB and spectral renderers agree — which is precisely the aliasing this skill would otherwise walk into. |

---

## 5 · The hydraulic jump, and standing structure in flow

**Status: absent.** `Froude` appears twice — as the wake's Froude number and as a shallow-water note
— and the hydraulic jump does not appear at all.

**Why it matters.** A rapid, a weir and a spillway are not travelling waves; they are **stationary
structures** where supercritical flow (`Fr > 1`) collapses to subcritical (`Fr < 1`) and dumps its
energy in place. A flow-mapped river surface scrolls texture over a bed and cannot produce one, so
white water in rapids gets authored by hand where it should fall out of the flow field.

| | |
|---|---|
| `P` | Bélanger, J.-B. — the momentum relation across the jump, giving the **conjugate depth** `y₂ = (y₁/2)·(−1 + √(1 + 8·Fr₁²))` with `Fr₁ = V₁/√(g·y₁)`. Closed form, immediately checkable, and the seed row this section would start from. |

⚠️ **A named limitation to carry with it:** the Bélanger relation neglects bed roughness, and a
rapid is the roughest bed there is — so the conjugate depth is the *structure*, not the energy
budget.

---

## 6 · Vortex structure: eddies, whirlpools, drain vortices

**Status: absent, and unsourced.** Zero mentions in either skill.

⚠️ **This entry has no verified anchor yet, and is recorded as an admitted gap rather than a
sourced one.** The other five carry a reference because one was found and checked; this one does
not, and inventing a plausible citation to make the table symmetric is exactly what `12b`'s
convention forbids. The eddy behind a boulder, the shed vortex street, the bathtub vortex and the
whirlpool are real, common, and currently outside everything here.

---

## The pattern, kept because it predicts

Two of these — ice and the free jet — were found by the same question, and both had the same shape:
**the subject was present and the axis was missing.** Snow was covered and ice was not, because the
phase axis was never drawn. Waterfalls were derived and hoses were not, because the Weber axis was
never drawn.

So the next place to look is not another subject. It is another **axis**: phase, confinement scale,
energy input, composition, and whether the structure travels or stands. Four of the six entries
above sit on an axis that this skill has never made explicit, and that is a better search than any
list of topics.
