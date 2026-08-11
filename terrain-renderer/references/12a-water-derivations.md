# Water Rendering — Derivations

The doctrine chapter `12` states *what is true*. This file states *where each of those numbers comes
from*: the premises, the algebra, and the failure mode that made each derivation necessary. It is
the working half of `12`, not a summary of it — nothing here is a restatement, and a reader who has
only `12` cannot rebuild the eikonal wake solve, the meniscus flux integral, the footprint kernel's
scale, or the sun-lobe normalisation from it. A reader who has this file can.

`reference-impl/` is the executable form of the same material — `field.py` (the surface),
`wake.py` (the wake), `render.py` (the light), `validate.py` (the arbiter). Code is not doctrine:
this file re-derives rather than transcribes, and where the algebra disagrees with what the
implementation ships, the disagreement is stated with both numbers ([What did not
reproduce](#what-did-not-reproduce)). Every derivation names the test that guards it, or says that
none does — that mapping, collected in [What checks what](#what-checks-what), is what makes a long
file trustworthy rather than merely long.

Provenance follows `00`'s tiers — **P** paper/book, **T** talk, **F** folklore/practice, **?**
claimed but unverified — with `12`'s local overload of **D**: in this chapter and this file it means
*measured on the reference implementation*, not `00`'s vendor documentation. A chosen constant is
never laundered into a derived one; `?` on a constant means *this number was picked*, and the
conclusions that survive it are marked as such. `P` on a line of algebra means the algebra was
re-derived and checked here, which is the only sense in which arithmetic has provenance.

Contents: [Conventions](#conventions-that-have-to-be-fixed-first) ·
[The submerged round jet](#1-the-submerged-round-jet) ·
[The stationary wake](#2-the-stationary-wake-by-eikonal-ray-tracing) ·
[The meniscus](#3-the-meniscus) · [Footprint filtering](#4-footprint-filtering) ·
[The reflected-slope ellipse](#5-the-reflected-slope-ellipse) ·
[The sun as lobes](#6-the-sun-as-lobes) ·
[The internal-reflection integrals](#7-the-internal-reflection-integrals) ·
[The gathers](#8-the-gathers) · [The caustic pass](#9-the-caustic-pass-as-a-forward-splat) ·
[Absorption and the dry-band calibration](#10-absorption-and-the-dry-band-calibration) ·
[What checks what](#what-checks-what) · [What did not reproduce](#what-did-not-reproduce)

## Conventions that have to be fixed first

**One rms slope.** Everywhere in `12` and here,

```
s = sqrt(<|grad h|^2>) = sqrt(<gx^2> + <gy^2>)          # TOTAL mean-square slope
```

The other respectable convention — the per-axis rms `sqrt(<gx² + gy²>/2)`, which is an isotropic
field's single-axis Gaussian width — is smaller by exactly `√2`. Both are called "the rms slope".
Mixing them is not cosmetic: a band *normalised* through the per-axis form to a target of 0.024 puts
`√2 × 0.024` of actual slope on the water, so the error is in the water and not only in the
printout, and a slope budget weighing one band against another is then being done with two units on
the two sides of the scale. Total mean-square slope wins because it is what the rest of the doctrine
speaks: Cox & Munk quote total mss, `F = 0.25·d·s·k` is written for it, and the chapter's far-field
figures are in it (`D`, `field.py`'s convention block).

For a superposition of plane waves the analytic twin is

```
s^2 = sum_i sl_i^2 / 2
```

where `sl_i` is component `i`'s slope amplitude — the `/2` is `<cos²>`, **not** a per-axis split.
That coincidence is exactly why the two conventions are hard to separate by eye, and why the rule
that matters is procedural: compute `s` in one function and never write the expression out again.

**Symbols.** `σ(k)` intrinsic angular frequency; `σ_t` surface tension (0.0728 N/m, clean water at
20 °C); `ρ` density; `a = √(σ_t/ρg)` capillary length; `n` refractive index; `θ_c = asin(1/n)`
critical angle; `d` depth; `s` rms slope; `k` wavenumber; `fp` pixel footprint on the water, in
metres. Where a Gaussian width appears it is named `σ_x` for its own axis, never bare `σ`.

**The constants the reference implementation uses**, so the arithmetic below is reproducible:
`n = (1.3320, 1.3348, 1.3400)` at 620/545/460 nm, `ρ = 1000`, `g = 9.81`, `ν = 1.004×10⁻⁶ m²/s`,
`d = 1.40 m`, sun elevation 21.0°. `12` quotes `a = 2.73 mm` from `ρ = 998`; the implementation's
`ρ = 1000` gives 2.724 mm. That 0.2% is the whole of the difference between the two files' capillary
numbers and is not worth reconciling — but knowing which `ρ` produced a printed millimetre is.

---

## 1. The submerged round jet

**Derived from:** Bernoulli through an orifice with a discharge coefficient; the self-similar free
round turbulent jet (`P`, Pope *Turbulent Flows* ch. 5; Rajaratnam *Turbulent Jets*); and a
stagnation-pressure scaling argument for the free surface. The two shear-flow constants are `P/?` —
the *structure* is textbook and web-confirmed, the numerical values are model knowledge and vary a
few percent across experiments.

### Nozzle velocity

Bernoulli across the eyeball fitting, with `C_d` the discharge coefficient:

```
U0 = C_d * sqrt(2 * dP / rho)
   = 0.92 * sqrt(2 * 0.80e5 / 1000) = 11.64 m/s        # 0.8 bar, 20 mm eyeball
```

`C_d ≈ 0.92` is `?` — a typical eyeball value, not measured. Volume flow `U0·πd²/4` is then
13.2 m³/h, which is the sanity check a plumber would apply.

### Spreading, decay, profile

A free round jet is self-similar downstream of its potential core:

```
r_half(s) = S * s                       S ~ 0.094      # linear spreading  (P/?)
U_c(s)    = B * U0 * d_nozzle / s       B ~ 5.8        # 1/s centreline decay (P/?)
U(r)/U_c  = exp(-ln2 * (r/r_half)^2)                   # Gaussian, half at r_half by construction
u'        ~ 0.25 * U_c                                 # axial turbulence intensity (P/?)
```

The `ln 2` is not a shape choice: it is what makes `r_half` mean *half-width at half maximum*, so
the two constants `S` and `B` are measured against the same profile that is evaluated.

**The geometric consequence is the whole reason this is modelled as a jet rather than as a painted
lobe.** The free surface is a *plane at perpendicular distance `h` from the axis* (`h` = fitting
depth, reduced along the axis by the tilt). The jet can only disturb it once it has spread that far,
i.e. once `S·s ≳ h`. So the disturbed patch is elongated along the aim and **starts downstream of
the fitting, not at it** — which is what a real return looks like, and which no authored envelope
gets right by accident.

### Surface deformation, and the constant that is genuinely unknown

An eddy of velocity `u'` presses on the surface with a stagnation pressure `~ρu'²`, which lifts it by

```
eta ~ C * u'^2 / g                              # C is O(1) and UNKNOWN  (?)
slope ~ eta / r_half = C * u'^2 / (g * r_half)  # the eddy's size IS the local jet width
```

`C = 1` was used. **The level this produces is therefore not defensible and the near/far *ratio*
is** — that is the entire status of this link, and it is the weakest step in the chain from
plumbing to pixels. Worse, the far field it is ratioed against is set by `WIND_RMS` and `REVERB_RMS`,
which are *chosen* (`?`); quoting `12`'s "0.016 short, 0.055 long" back as confirmation is circular,
because those figures were read off this implementation. What `12` asserts independently is that the
near field is roughly twice the far field, and that is the only number to judge the envelope by
(measured 0.122 near against 0.053–0.058 far, i.e. 2.1–2.3 — `D`).

### The depth cliff

Because `r_half = 0.094·s`, the slope the jet forces at the surface collapses with fitting depth:
**0.093 at 15 cm, 0.058 at 17.5 cm — which is the calm water, i.e. nothing left to find — and 0.012
at a typical 30 cm** (`D`, recomputed here: at the envelope peak `s_ax = 0.923 m`, `r_half = 86.7 mm`,
`U_c = 1.463 m/s`, off-axis factor 0.765, `u' = 0.280 m/s`, slope `= u'²/(g·r_half) = 0.092`). The
*depth* is the load-bearing input, not the fitting's plan position. A model that gets a visible boil
from a 30 cm fitting has something else doing the work.

```hlsl
// Surface slope forced by a submerged round jet, from geometry alone.
float jet_slope(float3 p, float3 origin, float3 aim, float S, float B,
                float U0, float d_nozzle, float eta_C)
{
    float3 r  = p - origin;
    float  sx = max(dot(r, aim), 0.05);              // axial station
    float  r2 = max(dot(r, r) - sx * sx, 0.0);       // squared perpendicular offset
    float  rh = S * sx;
    float  Uc = B * U0 * d_nozzle / sx;
    float  up = 0.25 * Uc * exp(-0.693147 * r2 / (rh * rh));
    return (eta_C * up * up / 9.81) / rh;            // eta/r_half;  eta_C is UNKNOWN
}
```

**Tests.** `validate.py` tier 2 measures `S`, `B` and the profile *off `drift()` itself* — half-width
ratio `r_half/s = 0.094`, decay `U_c·s/(U0·d) = 5.8`, profile `= 0.500` at `r_half` — and brackets
both constants against the literature ranges (0.086–0.096 and 5.7–6.1). It also checks the jet's
momentum flux against the nozzle's (0.858, inside 0.75–1.05) and `u'/U_c = 0.25` against 0.2–0.3.
**Nothing tests `eta_C`**, and nothing can: there is no external referent for it.

---

## 2. The stationary wake, by eikonal ray tracing

**Derived from:** the deep-water capillary–gravity dispersion relation; Doppler shift in a steady
current; Hamilton's equations for geometrical wave optics in a moving medium (`P/?`, Whitham —
attribution from model knowledge, not re-verified); wave-action conservation. This is the largest
single derivation in the chapter and the one most recently corrected, so what follows is the
*current* form.

### The Hamiltonian, and why H = 0

Deep water, capillary–gravity:

```
sigma(k)^2 = g*k + (sigma_t/rho) * k^3
```

In a steady current `U(x)` the absolute frequency seen in the lab frame is Doppler-shifted:
`H(x, k) = sigma(|k|) + k·U(x)`. A pattern **held steady in the lab frame has zero absolute
frequency**, so the wake is the level set

```
H(x, k) = sigma(k) + k . U(x) = 0
```

and the rays are that Hamiltonian's own characteristics:

```
dx/dt =  dH/dk = c_g * khat + U(x)
dk/dt = -dH/dx = -(grad U)^T k
dphi  =  k . dx                        # phase along the ray
```

**The failure mode this replaced, and it is the important paragraph.** An earlier version launched
the *gravity-limit* stationary root and flew the rays with the *gravity-limit* group speed while
evaluating `H` with the full capillary–gravity `σ`. Two wrongs that partly cancel: the wake looked
plausible, every ray-level diagnostic was self-consistent, and the only thing that could see it was
`H` refusing to be conserved. If `dx/dt` and `dk/dt` are not the flow of the same `H` the rays are
evaluated against, then `H` drifts by an amount **no step size can reduce** — which is precisely the
signature `validate.py` tests for (below). Both halves of the ray system and the launch condition
must come from one dispersion relation, and the reason to insist is that the near-cancellation makes
the defect invisible to everything except the conserved quantity.

### The stationary launch root — exact, not deep-water

A crest stands still when its intrinsic phase speed matches the opposing current component
`c = U·cos ψ`, i.e. `σ(k) = k·c`. Square, divide by `k`, and it is a **quadratic in `k`, not a power
law**:

```
sigma^2 = g k + (sigma_t/rho) k^3   and   sigma = k c
  =>  k^2 c^2 = g k + (sigma_t/rho) k^3
  =>  (sigma_t/rho) k^2 - c^2 k + g = 0
  =>  k = rho ( c^2 -/+ sqrt(c^4 - c_min^4) ) / (2 sigma_t),     c_min^4 = 4 g sigma_t / rho
```

**The discriminant's `4gσ_t/ρ` is exactly `c_min⁴`.** That is not a coincidence to be noted and
moved past — it is the whole reason one branch suffices. Minimising the phase speed
`c(k) = √(g/k + σ_t k/ρ)` gives `k* = √(ρg/σ_t)` and `c_min² = 2√(gσ_t/ρ)`, hence
`c_min⁴ = 4gσ_t/ρ`; and the quadratic's double root sits at `k = ρc²/(2σ_t)`, which at `c = c_min`
is that same `k*`. **So the fan limit `ψ_max = arccos(c_min/U)` and the launched wavenumber come
from one branch and cannot disagree.**

Take the minus sign (the gravity root, the longer of the two waves standing still in the same
current; the plus sign is a second, much shorter stationary wave), and multiply through by the
conjugate to kill the cancellation:

```
k = 2 g / ( c^2 + sqrt(c^4 - c_min^4) )
```

Two readings fall out of that form immediately. `c >> c_min` sends it to `g/c²`, the deep-water
limit. And at `c = c_min` the exact root is `k = √(ρg/σ_t)`, i.e. `λ = 2π√(σ_t/ρg) = 17.1 mm` —
`LAM_MIN`, the same wavelength the capillary–gravity minimum sits at — while `g/c²` gives 34.2 mm.
**A factor of two at the fan edge.** Launching the gravity limit while cutting the fan at the
capillary-aware `arccos(c_min/U)` takes the two halves of one condition from different branches, and
leaves the fan edge carrying a wave that does not in fact stand still (`|H|/σ = 0.088` at launch —
`D`).

The size of the deep-water error is closed form and worth carrying, because "good enough where the
wake lives" is a claim that has to be evaluated at both ends of the band:

```
k_deepwater / k_exact = 0.5 * ( 1 + sqrt(1 - (c_min/c)^4) )
    lambda 35 cm  ->  0.24% low
    lambda 20 cm  ->  0.73% low
    lambda 10 cm  ->  2.85% low
```

(`P`, recomputed here.) The implementation's comment quotes 0.2% "where the wake lives (10–35 cm)";
that is the 35 cm end. See [What did not reproduce](#what-did-not-reproduce).

*Mitigating and recorded rather than leaned on:* the source's radiation efficiency (below) is
~5×10⁻³ at the fan edge, so the old error landed on components that barely radiate. That bounds the
damage. It does not make the launched wave stationary, and `H` is conserved from whatever value it
starts at — **a launch off the branch stays off it.**

### Group speed, and its collapse on the stationary branch

`dx/dt = ∂H/∂k` demands the group speed of *the same* `σ`:

```
c_g = dsigma/dk = (g + 3 (sigma_t/rho) k^2) / (2 sigma)
```

The gravity limit `½√(g/k)` is not innocuous in this band: at `λ = 34 mm` the true `c_g` is
0.181 m/s against 0.116 (36% low), and at `λ = 17 mm` it is 0.231 against 0.082 — **a factor of
three**, because past `c_min` surface tension is the whole restoring force and `c_g` turns round and
*rises* with `k` while `√(g/k)` keeps falling. The wake shortens as it travels, so it walks straight
into the band where the limit is worst.

On the stationary branch itself the expression collapses. Substitute `g = c²k − (σ_t/ρ)k²` (the
quadratic, rearranged) and `σ = kc`:

```
c_g = (c^2 k - (sigma_t/rho) k^2 + 3 (sigma_t/rho) k^2) / (2 k c)
    = c/2 + sigma_t k / (rho c)
```

Half the phase speed **plus** a capillary term — and at `c = c_min` that term is itself `c_min/2`, so
`c_g = c_min` exactly. This is what keeps the transport speed from running to zero the way the
gravity form does, and it is why the wake's energy cutoff (below) bites later and more softly than
the gravity form made it.

```hlsl
// One dispersion relation; everything else differentiates or solves IT.
float sigma_w (float k, float g, float st_rho) { return sqrt(g*k + st_rho*k*k*k); }
float c_group (float k, float g, float st_rho) { return (g + 3.0*st_rho*k*k) / (2.0*sigma_w(k,g,st_rho)); }

// Exact stationary root of sigma(k) = k*c, cancellation-free.  c_min^4 = 4 g st_rho.
float k_stationary(float c, float g, float c_min)
{
    float c2 = c * c, cm2 = c_min * c_min;
    return 2.0 * g / (c2 + sqrt(max(c2*c2 - cm2*cm2, 0.0)));
}
```

### The launch fan, and the source spectrum that has to go with it

At an axial station with drift `U`, stationary wavevectors exist for `|ψ| ≤ arccos(c_min/U)` — about
**±78°** at this jet's Froude number `U/c_min ≈ 4.6`. **That fan is not the shape of the
disturbance**, and treating it as one is the second trap in this band. Energy travels at
`c_g·k̂ + U`, which on the axis is `U/2`, dips through the capillary–gravity minimum group speed
0.178 m/s, and returns to `c_min` at the fan edge — never more than 0.1% above `U/2`. The current
dominates, so the **energy** fan is narrow and aligned with the jet (42° for 90% of the slope
variance, measured off the reconstruction — `D`; `12`'s provenance section quotes ±19° from an
earlier run of the same measurement).

Summing plane waves over the 78° wavevector fan — the obvious implementation — sprays the whole
basin with fan-edge wavelengths, and **those carry the most slope of all**, since `slope ~ A·k ~
1/cos²ψ`. A 4 cm band then lands on the water with more slope than the rest of the pool put
together, and it is exactly the band that dissolves the bed caustics. The fan must not be sampled
directly; the rays must be integrated and the pattern allowed to land where the energy goes.

The stationary condition says *which* wavelengths can stand still. It says nothing about which get
excited, and leaving that out is the other half of the same trap. A forcing patch of rms size
`σ_src` radiates the Fourier transform of itself:

```
a0(k) = exp(-k^2 sigma_src^2 / 2)         # radiation efficiency of a finite source
```

so it cannot make waves short compared with its own coherence scale. Since launched *slope* goes as
`A·k ~ k·exp(−k²σ_src²/2)`, it **peaks at `k = 1/σ_src`** — which makes `σ_src` the one number here
a photograph can pin down rather than the geometry, and it is calibrated (`σ_src = 0.186·r_half`, set
to land the peak near 10 cm against observed 5–15 cm crest spacing) rather than invented. The scale
*runs* with the jet (`σ_src ∝ r_half(s)`), which is why crest spacing tightens toward the origin of
the pattern.

### Amplitude: wave action, and where the steady wake stops existing

Along a ray tube of width `W` taken from neighbouring rays,

```
A^2 * |dx/dt| * W = const               # wave action
attenuation: exp(-int alpha dt)
alpha_clean = 2 nu k^2                                    # Lamb, bulk (P/?)
alpha_film  ~ 0.35 k sqrt(nu omega)                       # inextensible film (P/?)
```

The film term is *structural*, not a tuned multiplier: an unstretchable surface film cannot slip, a
Stokes layer of thickness `√(2ν/ω)` forms beneath it, and the dissipation there dominates. It is a
factor 3–9 stronger over the 8–50 mm band and holds only at the short end — past ~10 cm the film
stretches and the surface behaves clean, so the two limits are blended **on wavelength**, which is a
statement about the film. This is the term that decides how far the wake reaches: the wake *shortens*
as it travels (`k = k_stationary(U cos ψ)` with `U` decaying), so it walks itself into the
film-damped band and dies. Integrating with the bulk value instead lets 5–10 cm waves ring across
the whole basin, loading the pool with short-wave slope and dissolving the bed caustic net.

Wave action alone runs away: `A` stays roughly flat while `k` rises fivefold, so the linear solution
makes the wake **four times steeper** downstream. The bound is physical, not a taper — when the
transport speed `|dx/dt|` falls to `c_min`, the pattern can no longer outrun the slowest wave the
surface supports, it stops transporting energy away from where it was made, and the film damping
consumes it in place. Same `c_min` as the fan limit and the Froude number, applied to the ray instead
of to the launch, and cumulative (energy lost is not recovered if the ray speeds up again).

### The finite-difference step, sized by the jet and not by the answer

`dk/dt` needs `∇U`, and a central difference of step `e` on a Gaussian of half-width `r_half`
carries a **relative** truncation error that is `(e/r_half)²` and nothing else. With
`f = M·exp(−b p²)`, `b = ln2/r_half²`, the central difference error is `(e²/6)f'''`, and
`f'''/f' = −6b + 4b²p²`, so on the axis the relative error is `−e²b = −e² ln2 / r_half²`.

The half-width **runs** with the station, so the binding case is the smallest `s` the rays sample:
at `s = 0.7 m`, `r_half = 66 mm`, and demanding relative truncation ≤ 10⁻⁴ gives
`e ≤ 66·√(10⁻⁴/ln2) = 0.79 mm`. There is no round-off floor to trade against — `U(x+e) − U(x−e)` is
~2×10⁻² m/s while the representation error of `U` is ~2×10⁻¹⁶, fourteen orders of margin — so the
usual `√ε` optimum is nowhere near and `e` is simply chosen for the geometry.

**And this is the second failure mode worth keeping.** A fixed `e = 10 mm` is `(10/66)²·ln2 = 1.6%`
of the gradient at `s = 0.7 m` and 3.1% at `s = 0.5 m` — a **`dt`-independent** error in `dk/dt`,
which puts a floor under `|H − H₀|` that no step size can lower. With the dispersion relation made
consistent but the step left at 10 mm, the drift stalls at 0.018 and the `dt`-halving ratio is 1.05;
at 0.5 mm the drift is 0.0013 and the ratio is 0.248 — the ¼ an RK2 scheme owes (`D`).

### The conservation test is the guard, and its shape is the point

```
Hn = ( sigma(|k|) + k . U(x) ) / sigma(|k|)          # dimensionless, evaluated along the ray
launch:      |Hn| == 0            (the stationary condition, exactly)
integration: max|Hn - Hn0| must fall by ~4 when dt is halved
```

**A drift that does not fall when `dt` halves is a formulation error, not a step-size one.** That
assertion has no tolerance in it: either `dx/dt` and `dk/dt` are the flow of the `H` the rays are
measured against, or they are not, and no step size fixes the second case. This is the single most
valuable property of writing the wake as a Hamiltonian system — it hands you a quantity that is
conserved *by construction* and therefore a test that cannot be satisfied by tuning.

### Reconstruction: the window must be wider than the wave it carries

Ray samples are deposited as Gabor atoms (local plane waves under a Gaussian window sized from the
ray tube). **A Gabor atom narrower than its own wavelength is not a local plane wave** — it is a
wavelet whose own spectrum is centred near `1/σ_window`, and thousands of them at incoherent phases
reconstruct a field whose slope energy sits at the *window* scale rather than the *wave* scale.
Deposited through 11 mm windows, a wake whose rays carried 27 cm reconstructed as 5 cm: a fourfold
error in the dominant wavelength, invisible in every ray-level diagnostic, and worth a factor of five
in `F` on the bed (`D`). The floor on the window is therefore the WKB validity condition — about half
a wavelength — and it is that, not the grid, that sets it.

One consequence for [footprint filtering](#4-footprint-filtering): the reconstructed field's
carrier and the scale that aliases are **different by about a factor of three** (a ~53 cm ray
carrier against ~17 cm of field slope energy — `D`; both move a centimetre or two as the launch
branch changes, and both are measured each run rather than tabulated, which is the point of measuring
them). What a pixel samples is the field, so the filter must act at
the field's scale. The exact operation is to convolve the wake grid with the footprint Gaussian
directly — a mip pyramid over `fp`, needing no wavenumber at all; the single global rescale in use
differs from it by 5% over the footprints this scene reaches (`?`).

**Tests.** `validate.py` tier 3 checks the launch against the exact stationary condition
(`|H|/σ = 4.9×10⁻¹⁶`, PASS) and the integrator by convergence (`d(dt/2)/d(dt) = 0.248` against a
tolerance of 0.6, PASS). Tier 2 pins the dispersion relation itself: `σ` and `dσ/dk` against
analytic forms, `c_min = 0.2312 m/s` against `(4gσ_t/ρ)^¼` and against the published 0.231,
`λ_min = 17.12 mm` against `2π√(σ_t/ρg)` and against the published 17.1, and the fan
`arccos(c_min/U) = 77.44°`. Tier 3 also checks the Gabor operator — a lattice of atoms reconstructs
a plane wave to 6×10⁻¹⁶, and an atom at the shipped window floor carries 1.12× its own `k` against
4.63× at a window 0.04λ wide, which is the failure mode above, measured. **Untested:** the wave-action
amplitude, the `c_min` transport cutoff (a choice of form), `alpha_eff`'s film blend and its 0.35
prefactor, and the deposit lattice the traced rays actually make.

---

## 3. The meniscus

**Derived from:** Young–Laplace for a two-dimensional interface against hydrostatic pressure, plus a
contact angle. Everything below except the contact angle is closed form.

### The profile

Let `φ` be the surface's inclination to the horizontal, `z` the height above the far-field level, `s`
arc length. Curvature of a 2-D interface is `dφ/ds`, and `dz/ds = sin φ`, so Young–Laplace against
hydrostatic pressure gives

```
sigma_t * dphi/ds = rho g z
sigma_t * sin(phi) dphi = rho g z dz                    # substituting dz/ds
sigma_t (1 - cos phi) = rho g z^2 / 2                   # integrating, z -> 0 as phi -> 0
z^2 = 2 a^2 (1 - cos phi) = 4 a^2 sin^2(phi/2)
```

```
z = 2 a sin(phi/2),        a = sqrt(sigma_t / rho g)
```

At the wall the surface meets the solid at contact angle `θ_c` measured from the wall, so its
inclination there is `φ_w = 90° − θ_c` and the climb is

```
h = 2 a sin(45 deg - theta_c/2) = a sqrt(2 (1 - sin theta_c))
```

— the two forms are identical, since `sin θ = 1 − 2sin²(45° − θ/2)`. **3.85 mm at perfect wetting,
2.72 mm at 30°, 1.41 mm at 60°.** The contact angle is the one free number in the whole fillet and it
is **unmeasured** (`?`): a clean PVC sheet is nearer 80°, a liner in service — permanently wetted and
biofilmed — is nearer 0°, and nobody has measured the reference one. Quote the climb as a range.

### The two differentials, and why both are needed

```
dz = a cos(phi/2) dphi                 # differentiating the profile
dz/dx = -tan(phi)                      # definition of the inclination
=>  dx = a cos(phi/2) cos(phi) / sin(phi) dphi          # horizontal extent of the facet
    ds = a cos(phi/2)            / sin(phi) dphi        # arc length of the facet
```

The first says **where** the facet is, which decides whether the coping's undercut sits in front of
its mirror direction. The second says **how much surface** there is. A derivation that keeps only one
of them either mislocates the occlusion or misweights the flux. Note the ratio `ds/dx = 1/cos φ` —
that is the foreshortening factor that appears in the integral below.

### The integral, and what it is divided by

A camera ray does not see the fillet; it sees a pixel. So what is computed is a **radiant intensity
per unit length of waterline**, `W/sr/m`:

```
I(v) = int_0^phi_w [ F(n.v) L_env(R(phi)) (n.v) / cos(phi)
                     - F(v_z) L_env(R_flat) v_z ] dx
```

**The subtraction is the fillet minus the flat surface it replaces**, and it does two jobs at once.
It prevents double counting — the water shader has already shaded that flat surface over the same
millimetres, so the term added here has to be the *excess*. And **it is what makes the integral
converge**: `dx` diverges logarithmically as `φ → 0` (`dx ≈ a dφ/φ`) while the bracket vanishes
linearly in `φ`, so the product tends to a constant and the far tail costs nothing. Drop the
subtraction and the integral is divergent, which is the sort of defect that shows up as a
quadrature-dependent answer rather than as an obvious error.

Writing the result back as an equivalent radiance on the still plane,

```
L_add(d) = I(v) * P(d) / |v_z|,      int P(d) dd = 1
```

with `P` the fillet's own `d`-profile **convolved with the footprint across the waterline**. Any
pixel integrating `L_add` over its footprint then gets `I(v) × (length of waterline it contains)`
divided by its solid angle and `r²` — correct at every scale, with no clamp. Where the fillet is
resolved, `P` is a profile; where it is not, the same expression is a flux spread over one pixel.
`12`'s "below ~1 px clamp the screen width and scale the intensity by the same ratio" is what this
degenerates to; doing it as a convolution gets both regimes from one expression and **cannot produce
the dashed line the clamp is warning about**.

*Placement caveat (`?` in the placement, never in the amount):* the convolution puts part of the flux
at `d < 0`, the wall side of the junction — where it physically belongs, since the fillet's top
stands `h` up the wall. Reflecting it back into the water side is flux-conserving and wrong by less
than the pixel it is already spread over.

### Reachability: the one specular feature that cannot fail, and the two conditions that gate it

The fillet holds **every** tilt from 0 to `φ_w` in one strip, so the mirror condition is met inside it
for anything bright in the sky. That is the standing claim. But a meniscus tilts only perpendicular
to its own waterline, so the reachable normals are a **one-parameter family in the (m, z) plane**:
with `t` the along-wall unit vector and `m` the poolward one, `n(φ) = sin φ · m + cos φ · z`.

Reflecting `v` about such an `n` leaves the out-of-plane component alone (`R·t = −v·t` for every `φ`,
because `n` has no `t` component) and rotates the in-plane part at **twice** the rate. With
`θ_v = atan2(v·m, v·z)` and `θ_l = atan2(L·m, L·z)`:

```
R(phi) . L = sin(A) sin(B) + cos(A) cos(B) cos(2(phi - phi*))          EXACTLY
A = asin(-v.t),   B = asin(L.t),   phi* = (theta_v + theta_l)/2
```

Two consequences, and neither is the azimuth rule of thumb:

- **The closest the mirror direction ever comes to the sun is `β = A − B`**, attained at `φ = φ*`,
  and it is zero exactly where `(L + v)·t = 0`. That is the half-vector residual, and because `v`
  sweeps along the wall as the eye is at *finite* distance, it is satisfied at **one point on each of
  the four walls**, not on two of them. "The sun is due west" does not by itself rule a wall out.
- **What rules a wall out is the coping.** The sun's mirror direction leaves at in-plane angle
  `θ_l`, and the fillet sits millimetres from a wall carrying a lip above it, so any wallward tilt at
  all is looking at the underside of the stone. `θ_l < 0` exactly when `L·m < 0`, so **the sun's line
  is reachable on a wall if and only if the sun is poolward of that wall's vertical plane
  (`L·m > 0`)**. This is the same statement as the coping's own shadow on the water, arrived at from
  the reflected side instead of the incident one — which is a useful cross-check to run, because the
  two are computed by different code and must agree.

So the test is a conjunction: **`L·m > 0` *and* `β` passing through zero somewhere the frame can
see.** A wall can pass the first and fail the second, and the sun's branch on the reference pool is
reachable on exactly one visible wall and hidden behind a coping arris there (`D`).

*One more term the resolved wave field contributes:* the along-wall slope tilts the fillet out of its
own plane, so `β` is not a property of the wall alone — it is where the wave field happens to carry
it. **That is why a real waterline sparkles along a stretch rather than glinting at one point**, and
why a probe computed off the mean surface finds nothing a few centimetres away.

*And the occlusion test must be a step, not a ramp.* On flat water a soft ramp in the coping test
stands in for the spread of normals inside one pixel; here the normal is a quadrature node, not a
distribution, and leaving it soft lets 11% of a `3.6×10⁵` sun through a coping it is entirely behind
(`D`). The transition sits at `φ = θ_v/2`, where the mirror direction runs parallel to the wall.

**What is not built, so it is not read as built:** the fillet also *refracts*, and the transmitted
column is ~10× the reflected one, so that term is potentially larger than this one. It needs traced
geometry rather than an environment lookup.

**Tests.** **None in `validate.py`.** The profile, the flux integral, the reachability algebra and
the convolution are checked only by the render's own probe, which reads the line off the same
function that draws it. The capillary length is tested (2.724 mm against `√(σ_t/ρg)` and against the
published 2.72). This is the largest untested derivation in the file, and the honest reading is that
its *algebra* is verifiable on paper — everything above is closed form — while its *implementation*
is not independently checked.

---

## 4. Footprint filtering

**Derived from:** the definition of a pixel's spatial integral, and Fourier arithmetic on it. No
physics beyond that, which is why it is exact.

A camera pixel integrates the surface over its own footprint. Write that footprint's normalised
weighting as `w(r)`. What the pixel is entitled to see of a plane-wave slope component of amplitude
`a` and wavevector `k` is

```
INT w(r) * a cos(k.(x+r) + ph) dr  =  a * W(k) * cos(k.x + ph)
W(k) = INT w(r) exp(-i k.r) dr                    # the footprint's transfer function
```

— exact, and it assumes nothing about the field, only about the footprint. So the per-band factor is
the kernel's own Fourier transform evaluated at **that band's** `k`.

### Which kernel, and why box and tent both fail

| `w(r)` | `W(k)` | Behaviour |
|---|---|---|
| Box, width `fp` | `sinc(k·fp/2)` | Zeros at `fp = λ, 2λ, …`; negative lobes to **−0.217**; envelope decays only as `1/(k·fp)` |
| Tent | `sinc²(k·fp/2)` | Positive, but still zeroed; `1/k²` |
| Gaussian, s.d. `σ_w` | `exp(−k²σ_w²/2)` | Positive, monotone, no zeros |

The box is the *literal* footprint of a box-filtered pixel and is the wrong choice, for the reason
that is the whole point of the exercise: **a factor that passes through zero and comes back negative
means a band fades out, returns phase-inverted, and fades again as the footprint grows with
distance** — a slow beat against distance, i.e. a moiré generator, which is the exact defect being
removed. Its envelope is also far too slow: at `fp = 5λ` a box still passes 6% of the amplitude,
oscillating.

The Gaussian is taken because (a) it is positive and monotone, so a band fades once and stays faded;
(b) it is the only kernel at once separable *and* isotropic, which is all a **scalar** `fp` with no
orientation is entitled to assume — the true footprint is an oriented parallelogram and pretending to
know its axes from one number is fake precision; (c) it composes, so footprint ⊛ reconstruction is
another Gaussian with variances added and nothing downstream re-derives it. That is the EWA argument.

### The scale, which has to be derived rather than assumed

Two candidate anchors, and only the second is the job being asked for:

```
(a) SECOND MOMENT. A box of width fp has variance fp^2/12, so sigma_w = fp/sqrt(12) = 0.2887 fp.
    This REPRODUCES the pixel's averaging -- and at the Nyquist wavenumber pi/fp it still passes
    exp(-pi^2/24) = 0.663 of the amplitude, 44% of the variance, straight into the fold.
(b) NYQUIST. Sample spacing is fp, so the shortest representable wave is lambda = 2 fp.
    Pin half AMPLITUDE there:
        exp(-(pi/fp)^2 sigma_w^2 / 2) = 1/2   =>   sigma_w = fp * sqrt(2 ln 2)/pi = 0.3748 fp
```

Reproducing a footprint and prefiltering for a footprint are different jobs. (b) is used; it is only
1.30× the second-moment match — the same deliberate mild over-blur that mip-mapping is — and it
reduces the whole filter to one checkable sentence:

> **A component is half gone when the footprint reaches half its wavelength**, and 94% gone (99.6%
> of its variance) when the footprint reaches its wavelength.

The half-variance footprint is smaller by `√2`: `λ/(2√2) = 0.354λ`.

### Three rules, each of which costs something to learn the other way

- **Amplitude, not variance.** Averaging is linear on the field, so `W` acts on the *field*; the
  resolved variance then falls as `W²` on its own. Multiplying the gradient by `√W` — "attenuate the
  variance by `W`" — puts `W` on the variance and `√W` on the field, and those are two different
  surfaces. What a shader reads out is a **field** (it computes a normal from it, and a normal is a
  field quantity); the variance is a *second* number and has to be handed over separately.
- **Per component, not per band.** A band spanning 17–70 mm has no single `k`. One nominal
  wavenumber removes its long half together with its short half; per component, a band *narrows* as
  the footprint grows instead of switching off, which is what "narrow the distribution" means.
- **The output pixel's footprint, not the subsample's.** The difference is a factor `SS` and it
  decides the answer: at 8 m the two are 8.6 mm and 25.8 mm while the wind band is 28 mm, so the band
  is comfortably resolved by the subsample grid and hopelessly aliased by the output grid (`D`). And
  the output rate is conservative for a second, independent reason: **shading is nonlinear in slope,
  so a slope field sitting at the subsample Nyquist still produces radiance harmonics well above
  it.** Band-limiting the slope to the sampling rate does not band-limit what the shader makes of it.

The removed variance, per component, is `a²(1 − W²)/2` along that component's own `k` — which is
`_plane_rms` written per component, so the tensor is a refinement of the one rms convention and not a
second one. Collapsing it with `vxx + vyy` is always legal. The saturating form `1 − √(1 − a²w²)`
differs from `a²w²/2` by 0.25% at the steepest slope in this basin and would be a second definition
of variance sitting beside the first; one definition wins.

**The ledger that catches a convention leak.** Resolved and removed must add in quadrature to the
unfiltered total. The check is not exact — removed is summed band by band while resolved is measured
on the summed field, so

```
res^2 + rem^2 - s0^2 = 2 * ( sum_ij C_ij(filtered) - sum_ij C_ij )
```

i.e. it holds up to the amount filtering changes how the bands overlap, which is zero for independent
bands and small for a finite realisation on a small patch. **A residual at the third decimal is
sample covariance and says nothing about the units; a residual that grows with `fp`, or one that
appears on a single band's own row, is the convention leak this check exists to catch** (`D`).

**Tests.** Tier 1 confirms `band_weight = 1` unfiltered at every `k`, `band_weight = ½` at
`fp = λ/2`, and `half_footprint(k) = λ/2` exactly. Be clear about what that proves: it checks that the
*implementation matches the derivation*, not that the derivation is right — the calibration choice
(b) has no external referent and cannot have one. Tier 3 checks the separable GEMM against the direct
point sum, filtered and unfiltered, to 5×10⁻⁸.

---

## 5. The reflected-slope ellipse

**Derived from:** `R = 2(n·v)n − v`, differentiated. Exact to first order in the slope perturbation.

Let the resolved normal be `n` and the unresolved slope be a zero-mean Gaussian 2-vector `δ` with
covariance `Σ` — that *is* the tensor the footprint filter removed. To first order the normal tilts by
`−δ`, and

```
dR = 2(dn.v) n + 2(n.v) dn
```

Put the incidence plane in x–z with `n = z`, `v = (sin θ_v, 0, cos θ_v)`:

- **`δ` along the view azimuth (in the plane).** `dn = (−δ_p, 0, 0)`, so `dn·v = −δ_p sin θ_v` and
  `dR = −2δ_p·(cos θ_v, 0, sin θ_v) = −2δ_p ê`. **The full factor two**, because the tilt swings both
  the normal and the incidence angle.
- **`δ` across it.** `dn = (0, −δ_q, 0)`, so `dn·v = 0` and `dR = −2 cos θ_v · δ_q ŝ`.
  **Foreshortened**, because an out-of-plane tilt only rotates the ray about the view direction.

```
J = diag(-2, -2 cos theta_v)          in the frame (in-plane, across-plane)
C = J Sigma' J^T                      Sigma' = the slope tensor rotated into that frame
```

**The reflection ellipse is therefore not similar to the slope ellipse.** The two axes scale
differently, so the eigenvectors move unless they were already aligned with the view azimuth, and the
result is stretched along that azimuth by `1/cos θ_v` — at a camera 33° above the horizontal
(`θ_v = 57°` from the normal) that is **1.8×**, an anisotropy the slope tensor never had. This is the
second independent reason a scalar roughness is wrong here; the first is that the removed slope is
itself anisotropic (a wind band is a spread about one azimuth, a wake is directional).

`ê` and `ŝ` are the two directions perpendicular to `R` — `ŝ` normal to the incidence plane, `ê`
completing it — so the offset to the light is just its two components in that frame and **no angles
are ever formed**, which matters because forming them near `R` is where the numerics go.

### Feeding it into a lobe

Two Gaussians convolve to a Gaussian whose covariance is the sum and whose **integral is unchanged**,
so the peak falls by `√(det Q₀ / det Q)`. Writing the widened lobe back as `cos^(n_eff)` rather than
as `exp(−n_eff θ²/2)` costs nothing and buys one property: at zero variance it is **bit-for-bit** the
unfiltered expression. Insist on that — a filtered path that does not reduce exactly to the
unfiltered one is a second shading model, and it will disagree with the first somewhere you are not
looking.

`n_eff` is **directional**: `1/(û^T Q û)` along the direction of the offset to the light, which is
how the anisotropy survives. On the axis (offset zero) every direction gives `cos^n = 1` and only the
peak factor does anything, so the fallback there is the mean variance.

### The companion term, without which filtering makes chrome instead of plastic

Plain Schlick is derived for a *smooth* interface; on a rough one the microfacets mask each other at
grazing incidence. Ship plain Schlick on a low-variance distant surface and the far band goes to a
near-100% mirror — the chrome-dome reading, which is the same defect as the plastic one seen from the
reflection side rather than the lobe side. Bruneton, Neyret & Holzschuch (2010) fit (`P`, used as
published, constants not re-checked against the paper's data):

```
F = R + (1-R)(1-cos theta_v)^5 * exp(-2.69 sigma_v) / (1 + 22.7 sigma_v^1.5)      sigma_v < 0.5
```

and `σ_v` is the **one-direction** slope rms along the view azimuth, not the total. It is fed the
*unresolved* variance only — the traced normal is the facet the pixel is actually looking at, so what
still needs masking is the sub-pixel remainder — which gives it the same boundary condition as the
lobe widening: identity as the footprint goes to zero.

**Tests.** Tier 3 checks `C11`, `C22` and `C12` against 400k perturbed reflections (agreement 1.6%,
1.1%, 1.4%) and the stretch against `1/cos θ_v` as an identity. The Bruneton constants are not
checked.

---

## 6. The sun as lobes

**Derived from:** the flux of a `cos^n` lobe, the solar angular radius, and single-scattering in a
plane-parallel Rayleigh atmosphere. Nothing is fitted.

### The disc: nothing free at all

A `cos^n` lobe carries, over the hemisphere, exactly

```
INT cos^n(th) dw = 2 pi INT_0^(pi/2) cos^n sin dth = 2 pi / (n + 1)
```

Setting that equal to the sun's own solid angle `Ω_sun = π θ_s²` gives

```
n = 2 / theta_s^2 - 1
```

and `2π/(n+1) = 2π/(2/θ_s²) = π θ_s² = Ω_sun` **identically** — not to leading order, identically,
given the small-angle `Ω_sun`. Then giving the lobe a peak of `L_sun = E_n/Ω_sun` makes its **flux
equal the direct beam exactly**. Peak, width and flux land on the sun together and there is no
amplitude left to choose, which is the point. At `θ_s = 0.265°`: `n = 93 493`,
`Ω_sun = 6.72×10⁻⁵ sr`, and (with `E_n = π·SUN_COL`, the convention a Lambertian `ρ·E/π` implies)
`L_sun = 3.59×10⁵` in green. Near the peak `cos^n θ ≈ exp(−nθ²/2)`, so the lobe's per-axis angular
variance is `1/n` — which is what the reflection ellipse above has to be compared against.

**The failure this replaces, priced.** A `cos^n` "sun" fitted by eye is an *aureole, not a disc*:
audited against its own constants, the hand-fitted lobe peaked **1563× below** the sun's radiance
over a solid angle **7.8× too wide**, and three lobes together carried 0.695 against a direct beam of
24.1 — a factor of 35 short (`D`). The symptom is not a dim sun; it is that glitter comes out as a
broad pale smear where the physics has small blinding points, which presents as a tuning problem and
is not one.

### The Rayleigh aureole

Single-scattered sunlight, from the same plane-parallel integral the beam obeys. Scattering at
optical depth `τ'` feeds the view direction at `F₀ exp(−τ'/μ₀) ω P(Θ)/4π`, attenuated out again; in
the sun's **own** direction `μ = μ₀` and the integral collapses to `F₀ m τ exp(−mτ) P/4π`. Since
`F₀ exp(−mτ)` is the beam that arrives, i.e. `E_n`:

```
L(Theta) = (E_n / 4 pi) * P(Theta) * m * tau_sca
```

with no free scale. Rayleigh's phase function `P = ¾(1 + cos²Θ)` splits into an **isotropic ¾** — a
uniform sky, which the elevation gradient already carries — plus `¾cos²Θ`, which is the whole of the
forward structure a Rayleigh atmosphere has. And `cos²` **is** a `cos^n` lobe with `n = 2`:

```
n_aureole = 2,     amp = (E_n / 4 pi) * m * tau_R * 0.75
```

Its flux is `amp · 2π/3 = E_n·m·τ_R/8`, so **total lobe flux / direct beam = 1 + m·τ_R/8** — a
closed-form identity the environment can be tested against. It is broad and faint (0.4 against a sky
of ~1.0), and that is the result, not a shortfall: **a clean atmosphere has no compact aureole,
because a compact aureole is a diffraction peak and diffraction needs particles.**

### The aerosol lobe, derived to zero

The reference sun's *colour* is `exp(−m τ_Rayleigh)` at its own air mass to one part in 10⁴ (`D`).
That fixes three things at once: the air mass is not free, the reddening is not a grade, and
**`τ_aerosol = 0` in the beam that lights the scene.**

> **Adding an aerosol aureole to the environment without removing it from the beam creates the light
> twice** — and creates it exactly where a reflection is most sensitive to it.

Dimming the beam instead means changing the sun colour, which relights every diffuse surface in the
frame. So the pair is deferred, not omitted, and the cost of the omission is measured rather than
guessed: rendered with `τ_a(550) = 0.10`, Ångström 1.0, ω₀ = 0.95 and half the coarse mode's
scattering in a 2° diffraction peak, it moved the mirror band's reflected median from 0.16 to 4.04 —
past the file's own white point — and took the far water to 245/255 with 98% of it over 200 (`D`).
**A frame shot along the sun's azimuth cannot hold both a hazy sky and a legible bed**, which is a
statement about the weather in the reference photograph as much as about the renderer.

The honest cross-check is the circumsolar ratio: a Rayleigh-only environment reads CSR ≈ 0.0004
against the ~0.05 measured for a clear sky, and **all** of that shortfall is the aerosol diffraction
peak derived to zero above (`D`).

**Tests.** Tier 1 checks `2π/(n+1) = Ω_sun`, `Ω_sun = πθ_s²`, `L_sun·Ω_sun = E_sun`,
`E_sun = π·SUN_COL`, the disc lobe's shipped flux against the direct beam, the on-axis peak radiance,
`total/beam = 1 + mτ_R/8` as an identity, the Hansen & Travis Rayleigh optical depth form, and that
`exp(−mτ)/red` reproduces the sun's colour to 10⁻³. Every one of these is closed form; there is no
tier-2 or tier-3 check on the sky, and the elevation gradient has no referent at all.

---

## 7. The internal-reflection integrals

**Derived from:** a Lambertian bed under a flat interface, and the critical angle. This section
contains the one derivation in the file that **does not reproduce as shipped**, and the algebra is
given in full for that reason.

### The horizontal receiver: `1 − 1/n²`

Everything a Lambertian bed emits beyond `θ_c = asin(1/n)` is totally internally reflected straight
back down. The flux fraction is a cosine-weighted hemisphere integral:

```
frac = INT_{tc}^{pi/2} cos t sin t dt / INT_0^{pi/2} cos t sin t dt
     = 1 - sin^2(tc) = cos^2(tc) = 1 - 1/n^2
```

**43.7% at `n = 1.333`, 44.3% at 1.34** — no fitting, no constant, and the same quantity as
`cos²θ_c`. This is the term whose absence makes a shaded bed a flat dark hole: flat sky ambient
through the Snell window cannot keep water under a shade sail at about half the lit value, and the
return is what does.

**It is not a local fill.** A ray leaving 1.40 m of water *at* the critical angle needs
`1.40·tan 48.6° = 1.59 m` of horizontal run to reach the surface, and steeper ones land further, so
the return is smeared over metres — which is why it is estimated on a coarse grid and reads as a lift
rather than a glow. In a basin 4 m across, **58% of it meets a wall first** (`D`), which makes the
wall the single largest unmodelled carrier of light in the scene.

**How big the wall is, exactly.** What a bed point sees of the sky is the water rectangle overhead,
and the cosine-weighted view factor from a horizontal differential element to a parallel rectangle is
closed form; split at the point's own `(x, y)` and sum the four quadrants:

```
F(a, b, h) = (1/2pi) [ (a/r_a) atan(b/r_a) + (b/r_b) atan(a/r_b) ],
             r_a = sqrt(a^2 + h^2),  r_b = sqrt(b^2 + h^2)
```

Everything left over is wall — 35% of the hemisphere on average, 77% at the worst texel (`D`) — and a
flat sky ambient applied over the whole hemisphere over-counts by exactly that share. It is not a
constant to be corrected either: the wall runs a factor 2.2 in red from waterline to foot, so what
replaces the flat constant has to be **directional**.

### The vertical receiver, re-derived

Now the ratio a vertical face collects relative to the horizontal bed the return map is normalised
for. **Start from radiance, not from flux.**

For a uniform Lambertian bed under a mirror, the downgoing radiance arriving at any point is `L` for
all `t > θ_c` — radiance is conserved along the ray and a perfect mirror preserves it, and a
Lambertian bed's radiance is angle-independent by definition. So

```
E_horiz = INT_{t>tc} L cos t dw            = 2 pi L INT_{tc}^{pi/2} cos t sin t dt = pi L cos^2(tc)
E_vert  = INT_{t>tc} L (sin t cos ph)^+ dw = 2   L INT_{tc}^{pi/2} sin^2 t dt

TIR_VERT = E_vert / E_horiz
         = ( pi/2 - tc + sin(tc) cos(tc) ) / ( pi cos^2(tc) )
         = 0.885     at n = 1.3348
```

Two sanity checks on that form. Over the **full** hemisphere it gives `(π/2)/(π) = 1/2` — a vertical
face collects exactly half of a horizontal one under a uniform hemisphere, which is the same ½ the
riser gather closes on. And `E_horiz = πL cos²θ_c = πL·(1 − 1/n²)` is `TIR_FRAC` times the bed's own
exitance `πL`, which is what the return map is normalised by, so the two halves are consistent.

**What ships instead, and why it is wrong.** The implementation writes the returning field as an
"angular density `cos t · sin t dt`" — the *emitted flux* distribution — and then multiplies by the
receiver cosine. That weighting is correct for a **flux fraction** (it is how `TIR_FRAC` is derived)
and wrong for a **receiver's irradiance from a distributed source**, because `cos t sin t` already
contains the horizontal receiver's own cosine. Carrying it into the vertical case leaves a spurious
`cos t` in the integrand. On top of that, the shipped expression carries a further stray `sin t`
relative to the prose beside it. Three numbers result:

| Form | Vertical numerator | Horizontal denominator | Ratio |
|---|---|---|---|
| **Shipped** | `∫cos t·sin³t dt/π = (1 − sin⁴θ_c)/(4π)` | `∫cos²t·sin t dt = cos³θ_c/3` | **0.563** |
| Stated derivation / `validate.py`'s expectation | `∫cos t·sin²t dt/π = (1 − sin³θ_c)/(3π)` | `∫cos²t·sin t dt = cos³θ_c/3` | **0.635** |
| **Correct (radiance)** | `2∫sin²t dt = π/2 − θ_c + sinθ_c cosθ_c` | `2π∫cos t·sin t dt = π cos²θ_c` | **0.885** |

(all integrals over `t ∈ [θ_c, π/2]`. `P`, derived and checked numerically here against a 4M-sample
uniform-solid-angle Monte-Carlo of the radiance field, which gives 0.8858 ± 0.0004.) Note that the
denominator moves too: the first two rows weight the *horizontal* receiver by the emitted-flux
density as well, so the error is not confined to the vertical half of the ratio — it merely fails to
cancel.

**Tests.** `TIR_FRAC` passes against a 2M-sample cosine-weighted Monte-Carlo and as an exact
identity. `_sky_vf` passes against 400k-sample Monte-Carlo at three geometries. **`TIR_VERT` FAILS
two rows** — against a quadrature of the integral its own comment states, and against a Monte-Carlo
of the same statement. Both those rows expect 0.635, so **fixing the code to satisfy the suite would
land on the middle column, which is also wrong**; the test and the code share one premise. That is
the interesting shape of this finding: an independent method agreeing with a wrong derivation because
it was written from the same sentence.

---

## 8. The gathers

**Derived from:** the definition of irradiance, and a change of variables. Three estimators, one
closure.

### The half-hemisphere a vertical face sees

A vertical face's cosine-weighted hemisphere splits **exactly** in half at the horizon: sky above,
receiver-facing world below. In the normalisation where `(1/π)∫cos dω = 1` over the hemisphere, each
half is **0.500**, and that number is a regression test on any quadrature that claims to integrate
one of them. The two halves partition the hemisphere, so a sky term over the upper half plus a gather
over the lower half counts nothing twice — which is the reason to write it this way rather than as a
form factor with an ambient fudge.

### The poolward-facet gather (stone, and the liner band)

For a facet at height `q` above the still plane, and a surface point at horizontal distance `ρ` and
bearing `φ` off the inward normal:

```
R^2   = rho^2 + q^2
(N.w) = rho cos(phi) / R                    # receiver cosine, horizontal poolward normal
dw    = (q/R) dA / R^2                      # the water element's own cosine, over R^2
=>  weight = rho cos(phi) q / R^4 dA = rho^2 cos(phi) q / R^4 drho dphi
    and on a LOG radial grid,  = rho^3 cos(phi) q / R^4 dln(rho) dphi
```

Two properties of that integrand carry the whole argument for the liner band as a receiver:

- **It is scale invariant on flat water.** `∫∫ρ²cosφ·q/R⁴ dρdφ = 2q·π/(4q) = π/2`, independent of
  `q`. A vertical facet over an infinite plane collects the same irradiance at 6 mm as at 600 mm, so
  the band is **not brighter than the coping because it catches more light**. Normalised by `π` this
  is again 0.500 — the same closure.
- **It peaks at `ρ = q`.** `d/dρ[ρ²/(ρ²+q²)²] = 0` at `ρ = q`. So the *patch of surface* a facet
  integrates shrinks with height: a facet 6 mm up reads a centimetre of water and resolves single
  caustic bands; one 120 mm up reads a decimetre; stone 300 mm back and 132 mm up reads half a metre
  and averages the net away. That is the mechanism — and measured on the reference pool it is **weak**
  (pattern contrast 0.17 at 6 mm against 0.14 at 120 mm and 0.16 for the stone at the lip, `D`),
  because 6–120 mm of blur is small against a 20 cm net. What the band actually wins is
  **orientation and area**, not contrast per unit area. Stating the mechanism and then measuring it to
  be weak is the useful outcome; asserting it would have been wrong.

The radial grid must follow the height (each height gets its own log grid from `0.25q` outward), or a
fixed floor misses the peak entirely for the low facets — which are exactly the ones the claim is
about.

### The riser gather: distance importance sampling with a closed-form weight

Sample `d` log-uniform on `[D₀, D₁]` and `φ` uniform on `(−π/2, π/2)` about the outward normal, then
aim at the point that far away on the plane through the face's own foot, `h` below the sample point:

```
beta  = atan(h/d)
w_hat = cos(beta) (cos(phi) n_hat + sin(phi) t_hat) - sin(beta) z
dw    = d h / (h^2 + d^2)^(3/2) dd dphi                    # solid-angle Jacobian
```

The Jacobian is `cos β dβ dφ` with `|dβ/dd| = h/(h²+d²)` and `cos β = d/√(h²+d²)`. With those pdfs
the estimator weight for `E = (1/π)∫L cos dω` is closed form:

```
w = ln(D1/D0) * cos(phi) * d^3 * h / (h^2 + d^2)^2
```

and **its expectation over the full range is exactly ½**:

```
E[w] = (2/pi) INT_0^inf d^2 h / (h^2 + d^2)^2 dd = (2/pi) * h * pi/(4h) = 1/2
```

The truncation to `[D₀, D₁]` is priced by the same antiderivative rather than absorbed:

```
closure(h, d0, d1) = (2/pi) [ f(d1) - f(d0) ],
f(d) = h ( -d / (2(h^2+d^2)) + atan(d/h) / (2h) )
```

so the light the lattice never sends a ray at is a **stated loss**, not a silent one. On the shipped
range (6 mm – 120 m) it is 0.499 of 0.500. The upper end is far past the basin diagonal on purpose:
those are the near-horizon directions that see the far wall, and cutting them off would show up as a
closure deficit rather than as a wrong picture.

*Where the estimator has to be sharp:* the fraction of the total weight inside `a` is
`closure(h, 0, a)/0.5`, which for `h = 0.12` and `a = 0.30` is **0.539** — half the irradiance comes
from inside 30 cm — and that is where the log spacing puts the samples.

### Why a fixed direction set convolves into a comb

**This is the failure the importance sampling exists to fix, and it is not a noise problem.**
Cosine-weighted directions are the right estimator for irradiance and they fixed the *colour* — but
they are drawn without reference to the bed, so 128 hit points land anywhere from 5 cm to 8 m away
and only ~10 fall inside any one 20 cm caustic cell. **The set was shared by every texel**, so that
under-resolution is not pixel noise: it is a fixed comb convolved with the caustic field, and it
produces a smooth blotch of the same amplitude as the pattern it is hiding (measured rms/mean
0.30–0.37, all of it at scales far coarser than a cell — `D`).

The fix is not more samples. It is that the sample points must form a **lattice that moves rigidly
with the receiver** — here a polar lattice about each texel, log-spaced so every octave of distance
gets the same number of samples. A lattice that moves with the receiver turns the gather into a
convolution with a smooth kernel, which is exactly what a near-field-dominated irradiance *is*; the
shared comb could not be. Nothing about the physics changed — same hemisphere, same cosine, same
traced occlusion.

*Whether the gather carries the net is then a measurement, not an assertion:* high-pass the map along
the arc at three cell widths and compare with the same high-pass on the bed radiance it is reading.
The ratio has a ceiling well under 1 — a receiver 100–300 mm from the bed integrates over about one
and a half cells, so **losing most of it is correct and losing all of it is not**. Measured: 11–18%
(`D`).

**Tests.** Tier 1 checks the full-range closure `= 0.500` exactly and the shipped-range closure
against `_ris_closure`. Tier 3 samples the shipped weight directly by Monte-Carlo and recovers the
closure to 0.4% — so **the estimator is validated, the map it produces is not**. The stone/band
gather is not tested at all.

---

## 9. The caustic pass, as a forward splat

**Derived from:** conservation of flux along a ray tube, plus Snell differentiated.

### The pass

```hlsl
// One ray per surface cell, carrying that cell's area.  Forward, not gathered.
for each cell (x, y) of a regular grid on the still plane:
    n   = normal_from_grad(grad(x, y))         // the SAME field the camera reads
    t   = refract(-sun_dir, n, 1.0 / ior)      // per-wavelength eta
    hit = trace(x, y, t)                       // bed, wall, or riser
    if (hit is a riser) continue;              // dropped rays ARE the cast shadow
    splat(map[hit.surface], hit.uv, sun_vis(x, y) * cell_area);
// then: divide every texel by its own area -> irradiance; blur per receiver depth.
```

Three points that are easy to get wrong and cheap to get right. The rays must be launched from the
*same* wave field the camera shades with, or the glint above the water stops sitting over the bright
line it caused. Rays that land on a vertical riser are **dropped**, and that is not an omission — it
*is* the step unit's cast shadow on the floor beyond. And the receiver's depth is whatever the trace
found, so nothing in the pass assumes a single depth.

### The focusing number, derived

A surface slope `s` turns the refracted ray by `s(1 − 1/n)`, so at depth `d` the landing point moves
by `d·s(1 − 1/n)`; focusing happens when the *gradient* of that displacement reaches unity. For
`h = a sin(kx)` under a vertical sun over a flat bed the whole pass is a 1-D map with an exact
Jacobian:

```
X(x)   = x + d tan(theta_n - theta_t),   theta_n = atan(h'),  sin theta_n = n sin theta_t
dX/dx  = 1 + d sec^2(theta_n - theta_t) (dtheta_n/dx)(1 - cos(theta_n)/(n cos(theta_t)))
small-angle:  dX/dx = 1 - d (1 - 1/n) a k^2 sin(kx)
```

So a fold exists iff `d(1 − 1/n)·a·k² ≥ 1`. Since `ak` is the slope **amplitude** while `s` is the
rms — `ak/√2` for one sinusoid — the doctrine's

```
F = d (1 - 1/n) s k  ~=  0.25 * d * s * k
```

reaches fold onset at `F = 1/√2 = 0.7071` **exactly** if the constant is exactly `1 − 1/n`. The
literal 0.25 in place of `1 − 1/n = 0.25082` moves that to `0.25/((1−1/n)√2) = 0.70478`, and
measuring the onset by bisecting on the sign of `min|J|` resolves the two: the measured onset is
0.70478. **The 0.25 is `1 − 1/n`, not a round number**, and the 0.34% between the two readings is the
chapter's own rounding, now identified rather than floating.

### The kernel: two blurs, added in quadrature

The caustic map is a **density estimate**, so its kernel has to satisfy two things at once — the
physical sun-disc penumbra, and the bandwidth below which the estimator's own shot noise beats the
signal.

*Penumbra.* Differentiating Snell gives the compression on entry:

```
sin(th_i) = n sin(th_t)   =>   cos(th_i) dth_i = n cos(th_t) dth_t
dth_t/dth_i = cos(th_i) / (n cos(th_t))            # ~ 1/n near normal incidence
penumbra(d) = 0.53 deg * cos(th_i)/(n cos(th_t)) * d / cos(th_t)
```

At the reference geometry (21° sun, `n = 1.3348`): compression 0.376, slant 1.958 m, **penumbra
6.81 mm at 1.40 m** — the number `12` quotes as the caustic sharpness floor.

*Estimator.* 33.6 M rays over 32 m² puts ~9.4 rays in a 3 mm texel, so a bare texel is
`1/√9.4 = 33%` noise. That sets a second, depth-independent bandwidth.

```
sigma(d) = sqrt( (penumbra(d)/4)^2 + sigma_est^2 )
```

**They add in quadrature because they are independent blurs.** The failure mode this replaced was a
flat "1.45× physical" multiplier, which hides the estimator term inside the physical one — and that
breaks the moment a receiver is 205 mm down instead of 1400 mm, because the physical part collapses
by 7× and the estimator's does not. A single blur for the whole map is the same bug seen from the
other side: it smears a 205 mm tread with a 1.40 m disc and flattens the very thing a step flight
exists to show. Where the depth field is piecewise constant, blurring per level and selecting is
exact rather than approximate.

`sigma_est` itself is `?` — chosen to leave the deepest kernel unchanged, so the change was a
re-derivation and not a re-tune. Say which of those two a change is; they are not the same claim.

**Tests.** The single most valuable row in the suite is the **sinusoid caustic**: for `h = a sin(kx)`
under a vertical sun the pass is exercised end to end through the render's own functions and compared
with the exact `1/|J|`. Below focus it matches to **0.086% pointwise** and conserves flux to 0.017%;
past focus it recovers the fold **count** exactly and their **positions** to 0.38 mm (two histogram
bins), and still conserves flux. Fold onset is checked against `0.25/((1−1/n)√2)` to 5×10⁻⁴, and the
`0.25 == 1 − 1/n` identity to 0.003. Tier 1 also checks the whole pass on a flat surface: one offset
for all rays, offset `= d·tan θ_t = 1.3696 m` along the sun azimuth, and a uniform map within shot
noise. **Not tested:** an oblique sun's obliquity factor, a sloped or stepped receiver, two crossed
sinusoids (where the Jacobian is a 2×2 determinant and folds become cusps), and the entry-height
approximation (rays launched from `z = 0` against a ±6.1 mm surface, ≤0.44% path error — stated as a
number rather than left out).

---

## 10. Absorption, and the dry-band calibration

**Derived from:** Beer–Lambert on a traced path, plus the observation that a pool's freeboard band
and its bed are **one pigment differing by one path**.

### The round trip

```
light leg   L_down = d / cos(theta_t)          # refracted slant, sun to bed
camera leg  L_up   = traced distance, bed to the surface point the ray entered at
T(channel)  = exp( -a * (L_down + L_up) )
```

Both legs are traced, not assumed: the light leg is the refracted slant (1.958 m for 1.40 m of water
at a 21° sun), the camera leg is whatever the view ray actually ran (median 1.96 m on the sunlit
floor of the reference frame). Beer–Lambert composes, so the round trip is one exponential over the
sum — which is the property that makes the next step work.

### The calibration

A liner pool's freeboard band above the waterline is **the same sheet** as the bed below it, with no
water over it. So

```
bed_radiance / dry_band_radiance  =  exp( -a * (L_down + L_up) )
```

and one frame containing both receivers calibrates **`a`, the liner colour, and both path lengths at
once** — with no reference chart, no second material, and no assumed albedo. That is the whole value
of the trick: it turns a photograph into an absorption measurement.

Two contaminations have to be divided out or the ratio measures something else:

- **The light leg is not pure sun.** Measured as `bed / bed-with-water-removed-from-the-light-leg`,
  the light-leg transmittance comes out *above* `exp(−a·L_down)`, and the gap is exactly how much of
  the bed's light is ambient and internally-returned rather than direct — light that did not take
  that path.
- **The receivers are not equally lit.** The raw picture ratio is dominated by the lighting: on the
  reference frame the only visible band is on a wall whose poolward normal faces away from the sun,
  so `N·L < 0` and it is a **shaded** receiver against a sunlit floor. Divide each receiver's own
  irradiance out before comparing, and the ratio lands on the round trip.

State the direction of the mechanism, too, because the intuitive reading is inverted. With `b_b ≈ 0`
a pool's water column has **no body colour and can only subtract**: it takes red (`a` is 0.275/m at
620 nm against 0.0145 at 460), and what survives *reads* as cyan. The band is not "the wall colour
without the cyan the water adds"; it is the same colour with nothing taken away.

### The companion: why a wet band is darker, with no free parameter

A film of water on a non-porous substrate darkens it by a mechanism that is entirely closed form.
Light crosses the interface twice and is trapped between the crossings by total internal reflection:

```
R_ext = INT_0^1 2 mu R_fresnel(mu) dmu          # cosine-weighted diffuse external reflectance
R_int = 1 - (1 - R_ext) / n^2                   # by reciprocity
a_wet = R_ext + (1 - R_ext)(1 - R_int) a / (1 - a R_int)
```

The last line is the geometric series `(1−R_ext)·a·(1−R_int)·Σ(a·R_int)^m` plus the first-surface
reflection. Two boundary conditions make it self-checking: `a_wet(1) = 1` (a perfect reflector loses
nothing) and `a_wet(0) = R_ext` (a bare interface over black). `R_ext ≈ 0.066`, `R_int ≈ 0.476`,
so a wetted liner reads about 0.8 of its dry albedo — **printed, not chosen**.

**Tests.** Tier 1 checks Beer–Lambert composition as an identity, transmittance over the refracted
slant, `slant/depth = 1/cos θ_t`, monotonicity in path length, and the chapter's own
`exp(−a·3.0)` figures. `R_ext` is checked against a converged quadrature, `R_int` against its
reciprocity form, and both `a_wet` boundary conditions exactly; tier 3 checks `R_int` against the
Egan & Hilgeman empirical fit (0.09% agreement — an independent method). Tier 2 checks the absorption
coefficients against Pope & Fry 1997 and Smith & Baker 1981, and **two of those rows FAIL**: the
implementation's blue is 48% above Pope & Fry at 460 nm (42% band-integrated). That is a constant
mismatch between the file and the published table, not a render error, and it propagates into every
number in this section — the round-trip blue is 1.7% dark over the shipped 3.92 m path. **The
dry-band regression itself has no test**; it is a measurement the frame makes, checked only against
the prediction from the file's own `a`.

---

## What checks what

`validate.py` runs in three tiers: **1** closed form (a disagreement is a bug in one of the two),
**2** published measurement (a disagreement may be a bug or a different water), **3** independent
method (a disagreement localises to one of the two methods).

| Derivation | Guarded by | Tier | Status |
|---|---|---|---|
| `U₀ = C_d√(2ΔP/ρ)` | — | — | **no test** (`C_d` is `?`) |
| `S`, `B`, Gaussian profile, `u'/U_c` | measured off `drift()`; bracketed against literature ranges; momentum-flux ratio | 2 | pass |
| `η ~ C·u'²/g` and the slope envelope | — | — | **no test**; `C` unknowable from the frame |
| `σ² = gk + σ_t k³/ρ`, `dσ/dk` | analytic forms | 2 | pass |
| `c_min`, `λ_min = 17.1 mm`, fan `arccos(c_min/U)` | published values + the `(4gσ_t/ρ)^¼` identity | 2 | pass |
| Stationary launch root `k = 2g/(c² + √(c⁴ − c_min⁴))` | `\|H\|/σ = 0` at launch, to 5×10⁻¹⁶ | 3 | pass |
| Ray equations + `c_g` consistency | `\|H − H₀\|` halving ratio 0.248 vs 0.25 owed | 3 | pass |
| Gabor window floor ≥ ½λ | atom carries 1.12 k vs 4.63 k at a narrow window | 3 | pass |
| Wave action, `c_min` transport cutoff, film damping | — | — | **no test** |
| Meniscus profile, flux integral, reachability algebra | — | — | **no test** (capillary length only) |
| `W(k)`, `σ_w = 0.3748·fp`, `half_footprint = λ/2` | closed-form identities | 1 | pass |
| Separable evaluation vs direct sum | grid vs point path | 3 | pass |
| `C = JΣJᵀ`, `J = diag(−2, −2cos θ_v)` | 400k perturbed reflections | 3 | pass (1–2%) |
| Stretch `= 1/cos θ_v` | identity | 3 | pass |
| `n = 2/θ_s² − 1`, `Ω_sun`, `L_sun`, disc flux | closed-form identities | 1 | pass |
| Rayleigh aureole flux `= mτ_R/8` of the beam | identity; Hansen & Travis `τ_R`; sun colour to 10⁻³ | 1 | pass |
| `TIR_FRAC = 1 − 1/n²` | identity + 2M-sample cosine-weighted MC | 1, 3 | pass |
| Rectangle view factor `_sky_vf` | 400k-sample MC at three geometries | 3 | pass |
| **`TIR_VERT`** | quadrature and MC of the stated integral | 3 | **FAIL — and see below** |
| Riser gather closure `= ½`, truncation | closed form + MC of the shipped weight | 1, 3 | pass |
| Stone/band gather (`ρ³cosφ·q/R⁴`) | — | — | **no test** |
| Caustic pass vs analytic `1/\|J\|` | 1-D sinusoid, below and past focus | 1 | pass (0.086%, folds to 0.38 mm) |
| `F = d(1−1/n)sk`; `0.25 = 1 − 1/n`; onset 0.70478 | bisection on `min\|J\|` | 1 | pass |
| Penumbra compression `cos i/(n cos t)`; 6.8 mm | differentiated Snell; traced slant | 1 | pass |
| Flat-surface degenerate case (offset, uniformity) | closed form | 1 | pass |
| Beer–Lambert composition, slant, monotonicity | identities | 1 | pass |
| `R_ext`, `R_int`, `a_wet` boundary conditions | quadrature; reciprocity; Egan & Hilgeman fit | 1, 3 | pass |
| `a(λ)` itself | Pope & Fry 1997; Smith & Baker 1981 | 2 | **FAIL in blue (+48%)** |
| Dry-band absorption regression | — | — | **no test** |

Also unguarded, and worth knowing before quoting any level from this material: the five-band
decomposition itself (`WIND_RMS`, `REVERB_RMS`, `JNEAR_RMS` are chosen, and the chapter's far-field
figures were read off the implementation, so they cannot confirm it); every material colour; the
tone map; and the whole camera pass. Cox & Munk can bracket the *total* slope and does — the basin's
total mss sits inside the `W = 0 … 1 m/s` band and the far-patch slope excess kurtosis sits inside
the −0.5…1.5 band on both axes — but nothing pins an individual band's level.

## What did not reproduce

Three checks done while writing this file disagreed with the implementation's own comments. All three
are recorded here rather than fixed, since this file does not own that code.

1. **`TIR_VERT` — the vertical-face internal-reflection ratio.** Shipped 0.563; the derivation stated
   beside it evaluates to 0.635; the correct value for a uniform Lambertian bed under a mirror is
   **0.885**. The stated derivation weights the receiver integral by the *emitted flux* density
   `cos t sin t`, which already contains the horizontal receiver's own cosine and so must not be
   carried into the vertical case; the shipped expression additionally has one `sin t` too many
   relative to that. The correct form is
   `(π/2 − θ_c + sinθ_c cosθ_c)/(π cos²θ_c)`, confirmed here against a 4M-sample
   uniform-solid-angle Monte-Carlo (0.8858 ± 0.0004) and against the full-hemisphere limit, which it
   sends to exactly ½. **`validate.py`'s two failing rows expect the middle number**, so satisfying
   the suite would replace one wrong value with another — the test and the code were written from the
   same sentence, which is the general hazard of validating a derivation against a restatement of
   itself. Full algebra in [§7](#7-the-internal-reflection-integrals).
2. **The wake's deep-water error claim.** `wake.py` says the gravity limit `g/c²` is "0.2% out where
   the wake lives (10–35 cm)". Recomputed from
   `k_deep/k_exact = ½(1 + √(1 − (c_min/c)⁴))`: **0.24% at 35 cm, 0.73% at 20 cm, 2.85% at 10 cm.**
   The claim holds at the long end only. It does not weaken the conclusion — the exact root is what
   ships, and the factor-of-two error at the fan edge is unaffected — but the band the approximation
   is safe over is narrower than stated.
3. **The riser gather's near-field share.** The comment writes
   `(2/π)∫₀^a d²h/(h²+d²)² dd = 0.539 at a = 0.30, h = 0.12`. That integral is **0.269**; 0.539 is
   the *fraction* of the estimator's total 0.500, which is what the sentence around it means. A
   labelling slip, not an arithmetic one — the conclusion (half the weight comes from inside 30 cm)
   is correct.
