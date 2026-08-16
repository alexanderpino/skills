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
[The static-equilibrium bay](#11-the-static-equilibrium-bay) ·
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
contact angle. The profile, the two differentials, the flux integral, the reachability algebra and
the projected-area identity are closed form; the contact angle is unmeasured (`?`); the transmitted
column's *source* is traced rather than derived, because the refracted ray goes somewhere specific
and near. Three transport terms were proposed, **two are built and the third is refuted below.**

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
per unit length of waterline**, `W/sr/m`. There are **two columns** and they run on one sweep, one
set of projected areas and one Fresnel:

```
I(v) = int_0^phi_w [   F(n.v)  L_env(R(phi))    (n.v)/cos(phi)      # reflected
                   + (1-F(n.v)) L_trace(T(phi)) (n.v)/cos(phi)      # transmitted
                   -   F(v_z)  L_env(R_flat)    v_z
                   - (1-F(v_z)) L_trace(T_flat) v_z             ] dx
```

`R(φ)` is the mirror direction and is an environment lookup; `T(φ)` is the **refracted** direction
and is not — it goes somewhere specific and near, and has to be traced. A third mechanism, total
internal reflection off the fillet's underside, was proposed and is **refuted below**: it subtends
zero solid angle from any camera above the water.

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

### The projected-area identity, which is what makes the whole thing checkable

Everything the two columns share is a pair of areas per node — the facet's projected area toward the
eye and the flat strip's. With `V` the direction **toward** the eye, decomposed on the wall's own
`(m, t, z)` frame,

```
w_fil = ds (n.V) = dx (n.V)/cos(phi),     w_flt = dx V_z
```

and because `ds sin φ = dz` and `ds cos φ = −dd` exactly, `∫ds(n·V) = ∫(V_m dz − V_z dd)`
**telescopes to its endpoints**. Subtract the flat strip of the same width and everything in the
middle cancels:

```
SUM (w_fil - w_flt) = V_m * z(phi*)          phi* = the steepest visible tilt
                    = V_m * h                whenever the eye is poolward
```

**The fillet's excess projected area is the poolward view component times the climb, and nothing
else.** Not the node count, not `dd/dφ`, not where the nodes sit — a quadrature that is wrong
anywhere in the middle still has to land here, and one that is wrong at either end cannot. On the
reference frame that is 0.83 mm per metre of waterline at the far end of the north wall and 2.30 mm
at the near end, against a flat strip of 3.0 and 8.3 mm: the fillet adds **28% more surface facing
the eye**, all of it within 15 mm of the wall.

The identity is blind to the *shape*, since it telescopes. So the shape is checked separately, by
solving the differential statement the closed form came from — see *Tests*.

### The transmitted column, and where the ray actually goes

Fresnel at the incidences this camera sees the fillet at is 0.02–0.07 near, 0.33 grazing. What the
facets **pass** is the complement, so the transmitted column starts 15–50× ahead of the reflected one
and the only question is what is behind it. Traced, with the file's own `refract` and `scene_hit`,
from each node's own place on the profile (`d(φ)` in from the waterline, `z(φ)` above the still
level):

- On the **north** and **west** walls — the two the reference frame sees — **all 64 facets face the
  eye and all 64 land on that wall's own liner**, between 1 and 119 mm below the waterline, over a
  leg of 20 to 175 mm of water. Not the bed: the wall, a few centimetres under the line, which is
  the brightest and least absorbed liner in the basin.
- On the **east** wall, where the eye looks poolward over the coping, 37 of 64 face the eye and they
  go the other way — 34 into the bed, 3 into the far wall, over legs of 0.3 to 1.6 m.

The result, in the same `W/sr/m` the reflected column is quoted in, on the north waterline:

| distance | reflected | transmitted | ratio |
|---|---|---|---|
| 9.41 m (x = 0.4) | 1.34e-4 | 2.74e-4 | 2.0× |
| 7.52 m (x = 2.4) | 9.88e-5 | 3.87e-4 | 3.9× |
| 5.70 m (x = 4.4) | 5.34e-5 | 5.93e-4 | 11× |
| 4.07 m (x = 6.4) | 1.97e-5 | 1.32e-3 | 67× |
| 3.46 m (x = 7.3) | 1.75e-5 | 1.23e-3 | 70× |

The reflected column **falls** along the wall, because the mirror direction runs away from the
horizon as the eye comes closer; the transmitted column **rises**, because `V_m` rises and the wall
it is looking at gets nearer and brighter. That crossover is why the shipped line was a bright patch
at the far end fading to nothing at the near one, and why the whole term now reads as a line.

*Two things this column used to inherit rather than own, both closed in the round after it was
written.* It carried `water_shade`'s **missing `1/n²`**, and it had to: what it subtracts was drawn
without it, and correcting one side alone would have put a 0.83-stop step across the junction. Both
sides now cross the interface inside `_menis_under`, which returns an air-side radiance — deliberately
there and not in the caller, so that the reflected and transmitted columns stay a partition of unity
in the caller's own units and the unit-radiance closure row keeps its "whatever `F` is" property. And
`scene_hit` used to place the submerged walls on the plan rectangle while the water surface ends at
`s = SLIP`, 20 mm inside it, so every traced hit — the fillet's and the flat baseline's alike —
landed about 5 mm lower on the liner than the geometry said; it very nearly cancelled in the
difference. The four planes now stand at `s = SLIP`, and the traced column lands between −45.7 and
+3.8 mm of the still line on the north wall where it used to land between −118.8 and −1.1 mm. Both
are written up in *What did not reproduce*, items 5 and 6.

### Self-occlusion, and the hole it left

A facet with `n·V ≤ 0` turns away from the eye. On a **near** wall that is every facet steeper than
`atan(V_z/|V_m|)`, because the fillet's own crest stands in front of them. Gating the fillet's term
on that is right; gating the flat term with it is not — the eye's rays over that stretch still carry
radiance, and what they carry is the crest, not nothing. Dropping both sides subtracts the whole
transmitted column over a centimetre of width and puts a hole there: **−2.1e-3 W/sr/m on the east
wall against +1.6e-3 on the west**. The defect was latent for as long as only the reflected half
existed — Fresnel 0.05 made the hole invisible — and building the transmitted half is what exposed
it. What now ships carries those nodes at the flat projected area, weighted with the radiance of the
last visible facet.

*And on a near wall that is still only a bound (`?`).* Where `V_m < 0` the fillet **folds in
projection** — `perp(d) = −V_z d + V_m z(d)` turns round at `φ*` — and a one-dimensional sweep over
`φ` cannot resolve a fold. What the eye really finds over the `|V_m|·h` of view the fillet vacates is
the liner band standing above the crest. The error is bounded by `|V_m|·h`: at most 3.9 mm of
projected area per metre of waterline, 2.3 mm at the east wall's own geometry, signed negative. **The
reference frame never reaches it** — the fillet is on a near wall only to the east and south, the
east waterline is behind the near coping's arris and 0% of the south's is in shot — and it is the
first thing to build if the camera moves to the other side of the pool.

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

### The third term, proposed and refuted

The proposal: looking down at the junction you look *through* water at the **underside** of the
fillet, and beyond the critical angle (48.5°) that underside is a perfect mirror — reflectance
exactly 1, against 0.02–0.07 for the external specular — showing the sunlit bed. The fillet sweeps
every tilt across ~5 mm, so the critical-angle condition is met inside it *by construction*: the same
argument that makes the meniscus specularly reachable, applied to a mechanism 15–50× stronger.

**It fails one step earlier, on arrival, and the reason is one line.** Write the transmitted
direction as `t = η i + f n` with `n` opposing the incident ray. Then

```
f = eta cos_i - cos_t,      cos_t = sqrt(1 - eta^2 + eta^2 cos_i^2)
f > 0  <=>  eta^2 cos_i^2 > 1 - eta^2 + eta^2 cos_i^2  <=>  eta^2 > 1
```

A camera above the water refracts **in**, `η = 1/n = 0.749 < 1`, so **`f < 0` strictly** — at every
incidence, with no grazing exception; its supremum is `η − 1 = −0.251` at normal incidence. A static
meniscus on a vertical wall carries tilts `φ ∈ [0, 90°]`, so its normal has `n_z = cos φ ≥ 0`, and a
camera above the water has `i_z < 0`. Hence

```
t_z = eta i_z + f cos(phi)  <  0        IDENTICALLY
```

**The refracted camera ray descends everywhere inside the water.** It cannot arrive at the underside
of a surface that lies above it. The fillet's underside subtends **exactly zero** solid angle from
any camera above the waterline — not a small angle, not one this frame happens to miss: zero, for
every eye position, every wall and every contact angle. Measured as well as derived: a scan of 1.29
million (wall, position along it, tilt) samples over all four walls found `t_z < 0` on every
front-facing one, worst case `−0.142`; a brute-force march of 215 000 refracted rays against the
analytic profile found **0** underside hits.

**The transferable part is the failure of the sweep argument.** Reachability of a *tilt* is not
reachability of a *position*. The fillet does hold every normal, and that is enough for the specular
term, where the eye and the source are both outside; it is not enough for a mechanism that needs the
ray to get behind the surface. The underside is reached only from below, by light already in the
water — which is the bed-return term (`TIR_FRAC` / `TIR_VERT`, §7), and which is built.

`MENIS_TIR_REACH = 0.0` records it in the implementation so that it cannot be rebuilt by accident,
and `validate.py` carries three rows on it.

**Tests.** **Eight groups, 39 rows, all passing — the term went from the largest unguarded
derivation in this file to one of the better guarded.** Every one of them is a statement the
implementation does not make about itself:

- **A force balance on the tabulated columns.** The weight the fillet raises per unit of waterline is
  carried by the vertical pull of the surface at the wall: `ρg ∫z dx = σ cos θ_c = σ sin φ_w`, which
  the profile integrates to `ρg a² sin φ_w = σ sin φ_w` identically. This is **Newton, not
  Young–Laplace** — it never appears in the derivation above, it constrains `z` and `dx` *jointly*,
  and it is evaluated on the very two columns the flux integral sweeps, so a table that is
  self-consistently wrong in either fails it. Closes to 0.003% on the shipped 64 nodes; tolerance is
  the midpoint rule's own error, measured by refining to 4096.
- **The shape, against an RK4 march of the differential statement.** The force balance pins the *area*
  under the profile and says nothing about its shape. So `dφ/ds = −z/a²`, `dz/ds = −sin φ`,
  `dd/ds = cos φ` is integrated as an initial-value problem from the wall outward. Nothing in that
  loop knows the answer is `2a sin(φ/2)`. Agrees to 4×10⁻¹⁴ m in `z`.
- **The projected-area identity**, `Σ(w_fil − w_flt) = V_m z(φ*)`, on both signs of `V_m` and at
  θ_c = 0/30/89°. 6×10⁻⁶ relative — it is exact for the continuum and the residual is the quadrature.
- **A brute-force ray march.** A 4000-ray parallel fan is cast at the RK4 polyline and each ray is
  marched — coarse grid to bracket, bisection to finish, because the crest is 30 µm of `d` and a
  uniform step fine enough to resolve it over 100 mm of march would be 4×10⁷ samples. What it
  measures is the projection *counted*, and unlike the identity it would notice a fold or an
  occlusion. Agrees to under 4 fan spacings.
- **The deposit, integrated back.** Hand `meniscus` a scene of **unit radiance** — sky, coping
  undercut and everything under the water all 1, sun off — and the two columns collapse to
  `F·w_fil + (1−F)·w_fil = w_fil` whatever `F` is. What the shipped function then deposits,
  integrated across the waterline and multiplied back by the `|v_z|` it divided out, must be the
  excess projected area. **One assertion over four separate things**: the node weights, the Fresnel
  split (which has to be a partition of unity across the two columns, not two independent
  weightings), the folded Gaussian's normalisation, and the fold at `d = 0`. None of them is
  computed anywhere as a total, so there is no line of `render.py` the row can be reading back.
- **Two limits, both forced.** As `a → 0` the fillet has no size; as `θ_c → 90°` it has no climb. The
  deposit must collapse **linearly** in each — that is what the identity forces, since
  `z(φ*) = 2a sin(φ*/2)`. This is the row that kills a missing subtraction: without it the integrand
  is `∫dx F L cos_i/cos φ`, whose `dx ≈ a dφ/φ` diverges logarithmically at the flat end, so it does
  not go to zero as `φ_w → 0` at all — it goes to a constant times `log N`. Checked at `a/10`,
  `a/100`, `a/1000` and at θ_c = 60/80/89/89.9°; at θ_c = 90° exactly the deposit is 7×10⁻¹³ m.
- **The reachability algebra against literal reflection.** `R(φ)·L` from the closed form against
  building `n(φ)`, reflecting and dotting, over 60 random `(V, L)`: 9×10⁻¹⁶. The closest approach is
  `cos(A − B)` to the scan's own grid error, and it reaches 1 exactly — the mirror direction passes
  through the sun — on 60 configurations *constructed* to have `(L + V)·t = 0`.
  *(Note on the convention: `v` in the formula above is the direction toward the **eye**, not the
  incident ray. With the incident ray the first term changes sign. The implementation is consistent
  with what is written here; a reader who substitutes the other `v` will get a residual of 1.8.)*
- **The refutation**, three rows: `f < 0` at every incidence as an algebraic sign, `t_z < 0` over
  323 400 front-facing samples of the shipped `refract`, and 0 underside hits out of the same.

What is **still not guarded**: the environment the reflected column reads (`_env_menis`) and the maps
the transmitted column traces into are stubbed out for the closure row, so what is checked is the
geometry and the split, not the radiance. The contact angle remains `?` and unmeasured, and every
row above is run across its whole plausible range rather than at one value.

### A floating body, and the split its own meniscus hides

**Derived from:** the same fillet, stood on a hull instead of a wall, plus one tangency.

Everything above solves the meniscus against a **vertical plane**, where the free surface leaves the
solid at `φ_w = 90° − θ_contact`. A floating body generalises it with one substitution and no new
physics: with perfect wetting (`θ_contact = 0`, this file's own choice) the surface leaves the solid
**tangentially**, so `φ_w` is the solid's own tangent angle at the contact line — on a sphere,
exactly the contact polar angle `β` measured from the lower pole. Nothing else in the fillet algebra
knows what it is standing on; the frame becomes radial (`m` outward from the body's axis, `t`
tangential) and the profile, the climb, the reach, the force balance and the projected-area identity
are all the wall's.

**The draught is then an output, not a parameter** — provided the body's mass and size are inputs
someone else fixed. Balance weight against the pressure integral over the wetted cap and the contact
line's own pull:

```
m = rho [ V_cap(beta) - z_w pi r_w^2 ]  -  (sigma/g) 2 pi r_w sin(phi_w)

    V_cap(beta) = pi h^2 (3R - h)/3,   h = R(1 - cos beta),   r_w = R sin(beta)
    z_w = 2 a sin(beta/2)                        the fillet's climb at the hull, a = capillary length
```

Two terms in that are the ones a naive Archimedes drops, and they pull the same way:

- the **`− z_w π r_w²`** is the divergence theorem taken against the **far-field** water plane rather
  than against the contact plane. The contact line stands `z_w` above the far field, so a cylinder of
  raised water sits inside the cap's projected area and is not displacement. Dropping it is the usual
  way this comes out wrong;
- the **line tension** acts along the free surface at the contact line, which here is *raised*, so
  its vertical component is **downward**. A floating body with a rising meniscus floats **deeper**
  than Archimedes alone puts it.

Worked on the reference implementation's float — a FINA size 5 water polo ball, `R = 0.11061 m`,
`m = 0.425 kg`, `σ = 0.0728`, and this file's own `ρ = 1000`, `a = 2.724 mm`:

| | |
|---|---|
| solved `β` | **50.07°** |
| draught `h` | **39.61 mm of a 221.2 mm ball — 17.90% of the diameter** |
| waterline circle | **169.6 mm** across |
| fillet climb `z_w` at the hull | **2.305 mm** (against 3.853 mm on a vertical wall, where `φ_w = 90°`) |
| the balance, in kg | displacement 0.4801, contact plane −0.0521, line tension −0.0030 → **0.4250** against `m` = 0.4250 |
| the two capillary terms | **13.0% of the weight** — Archimedes alone floats it at **37.11 mm**, 2.50 mm high |

(`D`, re-solved here by bisection on `β`; every row reproduces the implementation's own printed
figures to the digits it prints. `12`'s `ρ = 998` convention moves `β` by 0.03° and the draught by
0.04 mm, which is the only difference between the two files here.) The force balance
`ρg ∫z dx = σ sin φ_w` closes at **0.05582 N/m** on the float's own table, which is the wall's row
run at a contact angle the wall never reaches.

**Now the optical consequence, which is the part nobody predicts.** An above-water camera looking at
a floating body ought to see it cut in two at the waterline: the dry hull directly, and the wet cap
through the surface, displaced by refraction. Whether that split is visible at all is a **tangency**
condition, and the meniscus is in it.

A camera ray crosses the surface **outside** the contact circle — inside it there is no free surface,
only hull — and descends at `θ_w` from the vertical. Idealise the surface as flat at the far-field
plane and put the body's centre at `z_O = z_w + R cos β` above it. The limiting ray is the one that
enters at the contact circle's own radius, `x = −r_w`, and its perpendicular distance from the centre
is

```
p = | z_O sin(t_w) + r_w cos(t_w) |
  = z_w sin(t_w) + R cos(beta) sin(t_w) + R sin(beta) cos(t_w)
  = z_w sin(t_w) + R sin(beta + t_w)
```

so the ray reaches the hull iff `p < R`. And the touching point sits at height `z_O − R sin θ_w`,
which is below the contact line iff `cos β < sin θ_w`. The two together:

```
beta + t_w > 90 deg                          the touch is on the WET cap, not the dry hull
R ( 1 - sin(beta + t_w) ) > z_w sin(t_w)     the ray clears the raised contact line at all
```

Three consequences, in increasing order of how much they cost to learn the other way.

1. **With `z_w = 0` the condition is just `β + θ_w > 90°`.** Since `θ_w ≤ θ_c`, a floating sphere
   must sit at `β > 90° − θ_c =` **41.481°** — a draught deeper than `(1 − cos β)/2 =` **12.55% of
   its diameter** — before *any* above-water camera can see its wet half. That is a statement about
   floats in general and it disqualifies most of them: an inflatable rides at under 3%.
2. **The meniscus term is not a correction, it is the decision.** On the reference float at its own
   eye, `β + θ_w = 92.01°`, so the first test passes with 2° to spare and the second fails: the
   left-hand side is `0.11061 × (1 − sin 92.01°) =` **0.068 mm** against `z_w sin θ_w =` **1.541 mm**
   — short by a factor of **22.6**. A 2.305 mm climb is the whole of why that frame shows no split
   (`D`, recomputed here).
   **So "no split visible" is not evidence that the refraction is missing.** It is a prediction with
   a threshold, and the threshold involves surface tension.
3. **The threshold can be closed against the object's own catalogue.** At the window's most
   favourable exit angle, `θ_w = θ_c`, the pair of conditions needs `β >` **51.78°**, which through
   the flotation solve above is `m >` **0.480 kg** — outside FINA's 0.450 kg ceiling. So *no* camera
   splits *this* ball, and the closed form says so before a frame is rendered.

**The check that could not have been written from any of this**: fire the condition at the rays it
predicts. The reference implementation runs 396 pairs of `(β, θ_w)` at 4800 rays each through its
shipped ray–sphere intersector and compares the predicted flag with the traced answer. That row
caught the *first* version of this derivation, which compared the ray's slope against the hull's
tangent instead of finding the tangency, and disagreed on 196 of the 396 pairs (`D`).

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

### The base curve: the exact Fresnel equations, not Schlick

Before any roughness correction, the smooth-interface reflectance itself has to be right, and in a
*reference* that means the equations rather than a fit to them. With `sin t = sin i / n`,

```
R_s = ((cos i - n cos t) / (cos i + n cos t))^2          # E perpendicular to the plane
R_p = ((n cos i -   cos t) / (n cos i +   cos t))^2      # E in the plane
R   = (R_s + R_p) / 2                                   # unpolarised sunlight
```

(`P`, Born & Wolf §1.5.2.) The implementation shipped Schlick (1994),
`R ≈ F0 + (1 − F0)(1 − cos i)⁵`, at every water interface. Schlick's entire justification is that it
avoids the two square roots above; its error is quoted in the original as ~1% of `R` for common
dielectrics, and for water it is nothing of the sort. Measured against the exact equations at
`n = 1.3348`:

```
worst absolute, over 0-90 deg     exact 0.5163 against Schlick 0.5751 at 83.8 deg
over the frame's own incidence range (38-79 deg, measured in render.py),
    Schlick / exact - 1  =  -22.8% at 51.3 deg   (exact 0.0360, Schlick 0.0278)
                            +14.3% at 79.0 deg   (exact 0.3152, Schlick 0.3604)
                        crossing zero at 67.1 deg
the sun's transmission at 69 deg  exact 0.8774 against Schlick 0.8729
```

**The sign flip inside one frame is the finding**, not the grazing overshoot on its own. A one-sided
error is a candidate for absorption into some other constant; this one is a fifth *low* on the mid
water and a seventh *high* on the far water, so no single multiplier fixes both and the far band
reads more like a mirror than it should while the mid band reads less. The far water's specular term
is the brightest thing in the picture and the mid water is most of its area, so it lands on exactly
the pixels a reflection model is judged by, in both directions at once — in a file whose only
argument is being right. Measured on the frame: replacing the fit moved the spec-C corridor's median
reflected radiance from 0.020 to 0.024 (**+20%**, the sub-67° half) while taking the far-window mean
luminance down (the >67° half). An approximation whose whole justification is speed does not belong
in it; the exact form costs one `sqrt` and one divide per channel, measured at **+1.1% of a full
render** (5m23s → 5m27s at the reference resolution, all of this round's changes together — the
Fresnel calls are the compute part of that).

The premise-independent guard is the **Brewster identity**, and it is the sharpest test of a
reflectance model there is because it is a closed-form *number* rather than another integral. At
`θ_B = atan n` the p amplitude vanishes identically, `cos i = 1/√(1+n²)`, `cos t = n/√(1+n²)`, and

```
r_s = (cos i - n cos t)/(cos i + n cos t) = (1 - n^2)/(1 + n^2)
R(theta_B) = ((n^2 - 1)/(n^2 + 1))^2 / 2         # 0.03894 / 0.03948 / 0.04050 at the three IORs
```

No quadrature, no table, nothing to transcribe. Schlick reads 0.0306 there — **22% low** — while
passing every eyeball test of grazing behaviour, which is exactly why the guard has to be a value the
approximation cannot reach rather than a shape it can.

### The companion term, without which filtering makes chrome instead of plastic

The Fresnel equations are derived for a *smooth* interface; on a rough one the microfacets mask each
other at grazing incidence. Ship the smooth curve on a low-variance distant surface and the far band
goes to a near-100% mirror — the chrome-dome reading, which is the same defect as the plastic one seen
from the reflection side rather than the lobe side. Bruneton, Neyret & Holzschuch (2010) fit (`P`,
used as published, constants not re-checked against the paper's data):

```
F = R + (1-R)(1-cos theta_v)^5 * exp(-2.69 sigma_v) / (1 + 22.7 sigma_v^1.5)      sigma_v < 0.5
```

and `σ_v` is the **one-direction** slope rms along the view azimuth, not the total. It is fed the
*unresolved* variance only — the traced normal is the facet the pixel is actually looking at, so what
still needs masking is the sub-pixel remainder — which gives it the same boundary condition as the
lobe widening: identity as the footprint goes to zero.

Composing it with the exact base needs one substitution and no new choice. Bruneton's `r` attenuates
the interface's grazing **rise above `F0`**, and `(1 − F0)(1 − cos θ_v)⁵` was only ever Schlick's
model *of* that rise, so the implementation now evaluates

```
F = F0 + (R_exact(cos theta_v) - F0) * r,        r = exp(-2.69 sv)/(1 + 22.7 sv^1.5)
```

which puts the thing in place of the model of it and changes nothing else. Both boundary conditions
survive intact: `r → 1` gives exactly `R_exact`, `r → 0` gives `F0`.

**Tests.** Tier 3 checks `C11`, `C22` and `C12` against 400k perturbed reflections (agreement 1.6%,
1.1%, 1.4%) and the stretch against `1/cos θ_v` as an identity. Tier 1 checks the renderer's own
`fresnel` against the Brewster closed form to one ulp on all three channels, against `F0` at normal
incidence, and against an independently written evaluation of the same equations over 0–90°. The
Bruneton constants are not checked.

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

**And the aureole's *share* is bounded with no quadrature at all.** For any receiver, with whatever
weighting `w(ω)` its geometry imposes, the two halves of `P` integrate against the same weight, so

```
share = <(3/4) cos^2 Theta>_w / <(3/4)(1 + cos^2 Theta)>_w = <cos^2 Theta>_w / (1 + <cos^2 Theta>_w)
```

which is monotone in `⟨cos²Θ⟩_w ∈ [0, 1]`. Hence **≤ ½ for any receiver anywhere**, and **exactly
¼ integrated over the sphere**, where `⟨cos²Θ⟩ = ⅓` — independent of `τ`, of solar elevation, of
wavelength and of `F₀`, because `Θ` enters only through the phase function and its angular moments
are fixed. The identity runs backwards as a diagnostic: any claimed aureole share inverts to a
`⟨cos²Θ⟩_w` and a value above 1 does not exist. `10` spends this on a hand-written deck illuminant
whose aureole term implied `⟨cos²Θ⟩_w = 2.125` —
[the aureole has a ceiling](10-lighting-shadows.md#the-aureole-has-a-ceiling-and-no-quadrature-is-needed-to-find-it).

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
contained the one derivation in the file that **did not reproduce as shipped** — the implementation
has since been corrected to the value derived below, and the algebra is kept in full, with the two
wrong forms beside it, because the *way* the error survived a test suite is the transferable part.

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

### The refraction map past that angle, which has to return nothing

The same critical angle has a second consequence, on the other side of the interface and in code
rather than in an integral. Writing the transmitted direction as `t = η·i + f·n`, orthogonality of
the tangential part to `n` together with `|t| = 1` give `f = η cos i − cos t` with

```
k = cos^2 t = 1 - eta^2 (1 - cos^2 i),        eta = n_incident / n_transmitted
```

and `k < 0` **exactly** when `sin i > 1/η`, i.e. past `asin(1/η)`, which exists only for `η > 1` —
looking out of the denser medium. Past it there is no transmitted direction at all.

The implementation clamped `k` at zero and returned `η·i + η cos(i)·n` regardless: a vector of length
`η sin i > 1` lying flat in the interface plane. **Not a unit vector, not the TIR reflection, not a
flag — a direction that does not exist, returned silently.** Nothing downstream could tell it from a
real one, because nothing downstream measured its length. It is unreachable from every current call
site (all five refract *into* the water, `η = 1/n < 1`, where `k ≥ 1 − η² > 0`), and it is squarely on
the path of the underwater-camera pass, which is written entirely around this branch: outside Snell's
window the surface is a perfect mirror and *every* ray takes it.

The contract now is the null vector `(0,0,0)`, with `is_tir(t)` as the predicate. Zero rather than a
NaN or a fourth return value because it keeps the signature, it propagates to zero radiance rather
than to a poisoned frame, and it is checkable with one dot product.

**The premise-independent guard** is a conservation statement across two functions that share no line
of code: the angle at which `refract` stops returning a direction and the angle at which the exact
Fresnel reflectance reaches 1 are the **same angle**. One solves for `cos t` and tests its sign; the
other forms the s and p amplitude ratios. The suite bisects on `refract`'s own output for the onset —
no formula for the critical angle enters the measurement — and compares with a scan of `R(θ)`;
they agree to 10⁻⁴ deg, which is the scan's grid spacing. A second row checks the complement, that
sub-critical rays still come back as unit vectors, so "nothing transmits past TIR" cannot be passed by
a function that transmits nothing at all.

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

**What used to ship, and why it was wrong** (corrected in the implementation; kept here because the
*shape* of the error is the transferable part). The implementation wrote the returning field as an
"angular density `cos t · sin t dt`" — the *emitted flux* distribution — and then multiplied by the
receiver cosine. That weighting is correct for a **flux fraction** (it is how `TIR_FRAC` is derived)
and wrong for a **receiver's irradiance from a distributed source**, because `cos t sin t` already
contains the horizontal receiver's own cosine. Carrying it into the vertical case leaves a spurious
`cos t` in the integrand. On top of that, the shipped expression carried a further stray `sin t`
relative to the prose beside it. Three numbers resulted:

| Form | Vertical numerator | Horizontal denominator | Ratio | `θ_c → 0` limit |
|---|---|---|---|---|
| **Shipped until this round** | `∫cos t·sin³t dt/π = (1 − sin⁴θ_c)/(4π)` | `∫cos²t·sin t dt = cos³θ_c/3` | **0.563** | 0.239 |
| Stated derivation / `validate.py`'s old expectation | `∫cos t·sin²t dt/π = (1 − sin³θ_c)/(3π)` | `∫cos²t·sin t dt = cos³θ_c/3` | **0.635** | 0.318 |
| **Correct (radiance), and what now ships** | `2∫sin²t dt = π/2 − θ_c + sinθ_c cosθ_c` | `2π∫cos t·sin t dt = π cos²θ_c` | **0.885** | **½** |

(all integrals over `t ∈ [θ_c, π/2]`. `P`, derived and checked numerically here against a 4M-sample
uniform-solid-angle Monte-Carlo of the radiance field, which gives 0.8858 ± 0.0004.) Note that the
denominator moves too: the first two rows weight the *horizontal* receiver by the emitted-flux
density as well, so the error is not confined to the vertical half of the ratio — it merely fails to
cancel.

**The last column is the whole lesson.** Both wrong forms are perfectly good-looking integrals, and
either can be checked to arbitrary precision against a quadrature or a Monte-Carlo *of itself*. What
neither survives is a limit: open the cone to the full hemisphere and the answer is forced to be
exactly ½, by the same half-hemisphere argument the [riser gather](#the-half-hemisphere-a-vertical-face-sees)
closes on. A limit has no premise to share, which is why it is the check that was missing and the
check that is now there.

**Tests.** `TIR_FRAC` passes against a 2M-sample cosine-weighted Monte-Carlo and as an exact
identity. `_sky_vf` passes against 400k-sample Monte-Carlo at three geometries. `TIR_VERT` now passes
four rows: a quadrature and a 4M-sample Monte-Carlo, **both rewritten from the arriving radiance
rather than from the comment**, plus two that cannot share a premise with either — `tir_vert(0) = ½`
exactly, and that same ½ checked against `_ris_closure`'s full-range value, which is a
distance-importance-sampled view factor computed by unrelated code at the other end of the file.

*How this got into the suite in the first place*, since it is the reason the whole round exists: the
old quadrature **and** the old Monte-Carlo were both transcribed from the sentence beside the
constant, not from the interface. Two nominally independent methods reading one premise are one
method, and they agreed with each other on 0.635 while the code sat on 0.563. Satisfying the suite
would have moved the code onto the middle column — replacing one wrong number with another, with a
green run to certify it.

### The window and the mirror: two halves of one hemisphere

`TIR_VERT` answers what a vertical face collects from the **mirror** relative to the bed. The
question a renderer actually asks is the other one: what a vertical face collects from the **sky**,
which arrives only through the Snell window. Both come out of the same partition, and writing it in
one normalisation is what keeps them from being double-counted.

Normalise everything to `E_horiz(hemisphere)` — what a horizontal face at the same depth collects
from the whole in-water hemisphere under a uniform radiance `L`, which is `πL`. Then, with
`θ_c = asin(1/n)`:

```
E_vert (hemisphere) / E_horiz(hemisphere) = tir_vert(0)               = 0.5000
E_vert (t > tc)     / E_horiz(t > tc)     = TIR_VERT  = tir_vert(tc)  = 0.8853
E_horiz(t > tc)     / E_horiz(hemisphere) = 1 - 1/n^2 = TIR_FRAC      = 0.4387

    tir_vert(tc) = ( pi/2 - tc + sin tc cos tc ) / ( pi cos^2 tc )

mirror share of the vertical face   = TIR_VERT * TIR_FRAC             = 0.3884
window share of the vertical face   = 0.5 - TIR_VERT * TIR_FRAC       = 0.1116
                                                       -------------------------
                                          the two sum to tir_vert(0) = 0.5000
```

The last line is the check that makes the split trustworthy: the two shares are *defined* as a
partition of the vertical face's upper half, so they must sum to `tir_vert(0)` exactly, and they do
— which means an error in either one shows as an error in the other and never in the total.

**The `n²`, and why it is there.** The window share above is in units of the bed's *whole*
hemisphere, and what a renderer wants is the vertical face against the bed **for the same sky**. The
bed's own sky arrives through the same window and is `1/n²` of its hemisphere (the complement of
`TIR_FRAC`), so

```
window share of a vertical face, against a HORIZONTAL face at the same depth
    = (0.5 - TIR_VERT * TIR_FRAC) * n^2 = 0.1116 * 1.7817 = 0.1988
```

Per channel on this file's IOR triple: `θ_c = 48.655 / 48.519 / 48.268°`,
`TIR_VERT = 0.8881 / 0.8853 / 0.8801`, `TIR_FRAC = 0.4364 / 0.4387 / 0.4431`, and the window share
**0.1995 / 0.1988 / 0.1976** — a 1% spread, so one figure is honest at this precision (`D`,
quadrature and closed form here).

**What that costs when it is written as `0.5`.** `WALL_SKY = 0.5` is an exactly correct *partition*
of a vertical face's hemisphere and an exactly wrong *description* of what fills the upper half:
**77.7% of it is mirror and 22.3% is window**. The implementation handed a submerged vertical face
`WALL_SKY × WAO = 0.50 × 0.78 = 0.390` where the window's share is `0.199` — over-giving the sky by
**×1.96** — and the mirror that should carry the remaining 77.7% comes from the same one-bounce
truncation that delivers ×1.0217 of the closed series' ×1.2354. Over-count one half, under-count the
other, and the total can look right at any single level while the **hue** and the **caustic
structure** on that face are both wrong. The limit check that separates them costs nothing: zero the
sky and the face must fall to `0.777` of its upper-half irradiance — not to zero, and not to half.

**Do not merge this with the floor-lit-wall ceiling.** `L_wall ≤ ρ·L_floor/2` is about the *lower*
half of the same hemisphere — a form factor of exactly ½ to the adjoining diffuse plane — and its ½
is the same ½ as `tir_vert(0)` only because both are the half-hemisphere split. One bounds what the
**bed** can give a wall; this bounds what the **surface** can. They are additive, not alternative.

### One interface, two diffuse reflectances

This file and `12` both use the word "reflectance" for two different numbers, and the sections above
use one of them while [`12`'s composition](12-water-rendering.md#shading-and-optics) uses the other.
One flat water surface carries **two** diffuse Fresnel constants — the two directions through one
boundary — and nothing in a shader's spelling tells them apart:

```
R_ext = INT_0^1 2 mu R(mu; air -> water) dmu     arriving from the AIR and never entering    A LOSS
R_int = INT_0^1 2 mu R(mu; water -> air) dmu     arriving from the WATER and turned back     A TRAP
```

Same cosine-weighted measure `2μ dμ`, same unpolarised Fresnel formula, indices swapped. The
internal integrand is discontinuous at `μ_c = cos θ_c` — it is identically 1 below it — so the
quadrature is split there or it is wrong at the third digit:

| `n` | `θ_c` | `R_ext` | `R_int` | `R_int / R_ext` | `1 − 1/n²` (TIR) | `R_int − (1 − 1/n²)` (partial) |
|---|---|---|---|---|---|---|
| 1.3320 | 48.656° | 6.6248% | 47.3712% | 7.151 | 43.6373% | 3.7339% |
| **1.3348** | **48.519°** | **6.6690%** | **47.6166%** | **7.140** | **43.8735%** | **3.7431%** |
| 1.3400 | 48.268° | 6.7511% | 48.0681% | 7.120 | 44.3083% | 3.7598% |

(`D`, 2000-node Gauss–Legendre here, split at `μ_c`.) Three things follow, and each is load-bearing
somewhere in `12`.

**The two are tied, so neither is free.** Walsh's relation `n²(1 − R_int) = 1 − R_ext` holds on
these quadratures to **6×10⁻¹¹** — float64 noise, not agreement to a tolerance — which is what makes
it a guard rather than a restatement: the two integrals are computed from different index pairs and
the identity is a statement about the `L/n²` law plus Fresnel reciprocity, so it pins the
**exponent** and not merely the presence of a factor (at `n¹` the two sides part by 25%, at `n³` by
33%).

**`R_int` decomposes exactly, and the larger piece is not Fresnel at all.** Past `θ_c` the
reflectance is exactly 1, and the cosine-weighted flux beyond `θ_c` is `cos²θ_c = 1 − 1/n²`. So

```
R_int = (1 - 1/n^2)                                geometry: R = 1 exactly for every mu < mu_c
      + INT_{mu_c}^1 2 mu R(mu; water -> air) dmu  partial Fresnel INSIDE the cone
      = 0.438735 + 0.037431 = 0.476166            at n = 1.3348
```

**92.1% of the internal return is the mirror outside Snell's window** and 7.9% is partial Fresnel
inside the cone. That is why `1 − 1/n²` and `R_int` are so often confused with each other as well as
with `R_ext`: they differ by 3.74 points, which is small enough to hide and large enough to matter —
using `1 − 1/n²` where `R_int` belongs costs 1.9% of a red trap and 12.2% of a blue one
([the truncation table in `12`](12-water-rendering.md#the-upgoing-half-traced-the-return-leg-the-mirror-and-the-fixed-point)).

**And `1 − 1/n²` is the constant that whitens foam.** An air bubble seen from the water side is the
same water→air interface as the surface seen from below, so it has the same critical angle and
mirrors the same `43.874%` of everything that strikes it. One number runs the mirror outside Snell's
window and the opacity of whitewater; a renderer that derives one and paints the other has
special-cased one face of a single constant. The bubble side is
[`12`'s aerated water](12-water-rendering.md#aerated-water-foam-spray-and-whitewater).

**The directional pair, for the same reason.** `R_ext` and `R_int` are hemispherical means and are
correct only for hemispherical quantities; per direction, use `R(θ)` on the right index pair and read
the internal one at its conjugate air-side angle (Stokes reversibility). On this chapter's own sun
positions the external value is nowhere near either diffuse constant:

| | normal | 32.78° (a 57.22° sun) | 68.98° (a 21.02° sun) | diffuse |
|---|---|---|---|---|
| `R_ext(θ)` at `n = 1.3348` | 2.056% | **2.217%** | **12.241%** | **6.669%** |

(`D`, exact unpolarised Fresnel here.) A "surface reflection" quoted as one number is therefore
under-specified twice over — which side of the boundary, and averaged over what.

### The window from below: Snell's Jacobian, and where the horizon goes

**Derived from:** Snell's law differentiated. Nothing else enters.

The partition above says how much of a submerged receiver's hemisphere is window. This says **where
inside the window each part of the air world lands**, which is the question a submerged *camera*
asks and a submerged diffuse face never does.

Snell's law maps the air hemisphere onto the window one-to-one. Differentiate it and take the ratio
of the two solid-angle elements:

```
sin(t_a) = n sin(t_w)              =>   cos(t_a) dt_a = n cos(t_w) dt_w

dOmega_w / dOmega_a = ( sin(t_w) dt_w ) / ( sin(t_a) dt_a )
                    = ( sin(t_a)/n ) / sin(t_a) * cos(t_a) / ( n cos(t_w) )
                    = cos(t_a) / ( n^2 cos(t_w) )                              # azimuth is untouched
```

That is the weight any audit of the window has to be taken with, and it has a closure that needs no
renderer in it: integrated over the whole air hemisphere it must return the window's own solid angle,

```
INT_{air hemisphere} cos(t_a)/(n^2 cos(t_w)) dOmega_a  =  2 pi ( 1 - cos t_c )
                                                       =  2.12139 sr   at n = 1.3348
```

(`D`, Gauss–Legendre here: `2.1213850054` against `2π(1 − cos θ_c) = 2.1213850054`.) A stratified
estimator that closes on this is measuring shares *of* something; one that does not is reporting
percentages of an unknown denominator.

**Where the horizon goes.** The Jacobian's numerator vanishes at grazing, so the map crushes the
whole low-elevation air world into a thin annulus just inside the rim:

| air, `θ_a` from vertical | elevation | lands at `θ_w` | share of the **air hemisphere** beyond it | share of the **window** beyond it | concentration |
|---|---|---|---|---|---|
| 0° | 90° | 0.000° | 100.00% | 100.00% | 1.00× |
| 30° | 60° | 21.999° | 86.60% | 78.44% | 1.10× |
| 45° | 45° | 31.988° | 70.71% | 55.03% | 1.29× |
| 60° | 30° | 40.452° | 50.00% | 29.20% | 1.71× |
| 70° | 20° | 44.748° | 34.20% | 14.17% | 2.41× |
| 75° | 15° | 46.357° | 25.88% | 8.23% | 3.14× |
| 80° | 10° | 47.544° | 17.36% | 3.75% | 4.63× |
| 85° | 5° | 48.273° | 8.72% | 0.95% | 9.17× |
| 89° | 1° | 48.509° | 1.75% | 0.04% | 45.7× |
| 90° | 0° | 48.519° | 0 | 0 | → ∞ |

(`D`, closed form here at `n = 1.3348`.) **Half of the air hemisphere lives in the outer 29% of the
window, and the last ten degrees of elevation live in 3.75% of it.** The concentration diverges at
the horizon, which is the whole content of the law: an environment lookup taken from under the water
is a lookup into a map whose sampling density goes to zero exactly where the world is densest.

**So the naive parameterisation is wrong in a specific direction.** Index the window radially by
`θ_w`, or by the disc radius, or by an equal-area map of the *water-side* hemisphere, and the
samples are spread by `dΩ_w` — which is the wrong measure by the Jacobian above. Priced on a
`θ_w`-uniform radial map:

- the **innermost 10°** of `θ_w` takes **20.6%** of the radial samples and carries **2.72%** of the
  air hemisphere — over-served **7.6×**, and it is the zenith, where a sky is smooth;
- the **outermost 1°** of `θ_w` takes **2.06%** of them and carries **17.58%** of the air hemisphere
  — starved **8.5×**, and it is where every horizon-line object in the scene is stacked.

**The correct radial variable is the air-side cosine**, because equal solid angle in air is equal
steps in `cos θ_a`:

```
v = cos(t_a) = sqrt( 1 - n^2 sin^2(t_w) )        v = 1 at the window's centre, v = 0 at its rim
```

Uniform in `v` is uniform in air solid angle by construction — `1 − v` **is** the share of the air
hemisphere outside that ring, which is the middle column of the table above read off directly. The
operational form is simpler than the algebra: **refract first, look up second.** Store and sample
the environment as a function of the *air* direction and let Snell's law choose the sample, rather
than storing a window-space disc and hoping its texel grid lands where the world is. When a
window-space table is unavoidable — a cached disc for a fixed camera depth — make its radial
coordinate `v`, not `θ_w/θ_c` and not `r/r_max`.

**Two routes to the same audit answer different questions, and they will not agree line by line.**
Weighting a rendered frame's transmitting subsamples by their own solid angle measures *what this
picture spends its window on*: the camera's exit points and directions are a biased sample of the
interface, chosen by where the photographer stood. Weighting directions off the hemisphere with the
Jacobian above measures *what the window contains*, which is a property of the scene and the
interface and of no camera. On the reference implementation the two agree on the non-sky **total** to
0.13 percentage points and disagree on individual entries by up to **4.6×**
([`12`](12-water-rendering.md#what-the-window-actually-contains-and-why-the-rim-is-where-the-world-is)) —
which is not a discrepancy to reconcile. Quote route 1 for a cost or a visibility question and route
2 for a physics one, and never mix an entry from one with a total from the other.

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

(The *name* is `12`'s own, not a standard dimensionless group — see [the vocabulary
rule](12-water-rendering.md#the-vocabulary-and-which-half-of-it-you-can-look-up). What follows is
the derivation; everything in it is standard.)

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

### The diffuse exit, and why its two factors may not be separated

The round trip above is one *ray*, whose `μ` is known. The pool's own apparent albedo is the same
transport over a **distribution** of rays — a Lambertian bed emits over a cosine law — and that is
where a product of two respectable averages stops being the transport.

**The measure, first.** A Lambertian bed's flux leaves over the cosine-weighted density `2μ dμ` on
the water-side cosine, normalised: `∫₀¹ 2μ dμ = 1`. Two things then happen to a pencil at cosine
`μ`, and **both are functions of `μ`**: it crosses `d/μ` of water, and it meets an internal
reflectance `R_int(μ)` that is 1 past the critical angle and the exact unpolarised Fresnel inside
it. So

```
T_esc(tau) = INT_0^1 2 mu exp(  -tau / mu) (1 - R_int(mu)) dmu     # escapes on this pass
G_rt (tau) = INT_0^1 2 mu exp(-2 tau / mu)      R_int(mu)  dmu     # returned, and back at the bed

    tau = a*d  (vertical optical depth).  Both -> the diffuse constants as tau -> 0:
    T_esc(0) = 1 - R_int = 0.5263 / 0.5238 / 0.5193,  G_rt(0) = R_int = 0.4737 / 0.4762 / 0.4807

rho_water = (1 - R_ext(theta_sun)) * T_slant * rho_bed * T_esc / (1 - rho_bed * G_rt)
```

and because the bed redraws the direction from a cosine law at **every** bounce, the trap really is
geometric in `ρ_bed·G_rt` and the closed series loses nothing.

**The separated writing, and its error.** The tempting form takes the diffuse slab transmittance
`⟨T⟩ = 2E₃(τ)` and the diffuse exit constant `1 − R_int` and multiplies them. That is the product of
two means where the mean of a product is wanted, and the identity is exact:

```
<f g> = <f><g> + Cov(f, g),        <f g>/(<f><g>) - 1 = r * CV_f * CV_g
```

The correlation is not incidental and its **sign differs between the two legs**: a steep ray escapes
*and* crosses less water (positive), while a grazing ray is totally reflected *and* crosses more, so
the reflectance is large exactly where the round-trip transmittance is small (negative).

| At this pool's `τ = a·d = 0.3664 / 0.0742 / 0.0143` | Joint | Separated `⟨f⟩⟨g⟩` | Separated reads |
|---|---|---|---|
| `T_esc` | **0.3403 / 0.4795 / 0.5106** | `2E₃(τ)·(1−R_int)` = 0.2850 / 0.4563 / 0.5050 | 16.2 / 4.8 / 1.1 % **low** |
| `G_rt` | **0.0965 / 0.3277 / 0.4445** | `(2E₃(τ))²·R_int` = 0.1389 / 0.3614 / 0.4546 | 43.9 / 10.3 / 2.3 % **high** |

(`D`, 2000-node Gauss–Legendre here on the exact internal Fresnel; the correlation coefficient under
`2μ dμ` is **+0.76** on the escape leg and **−0.85** on the round trip at the red channel's `τ`, and
both tend toward ±0.90 as `τ` grows.) The error is monotone in optical depth and is already 3.6% at
`τ = 0.05`:

```
tau            0.05    0.10    0.20    0.37    0.50    1.00    2.00
escape leg    +3.6%   +6.6%  +12.0%  +19.4%  +24.6%  +39.6%  +58.4%   (joint over separated)
round trip    -7.3%  -13.2%  -22.9%  -35.5%  -43.6%  -64.2%  -83.2%
```

**Why it survived, and what it took to catch.** The two errors carry opposite signs and the round
trip sits in a denominator, so they partly cancel: on this pool the composed `rho_water` moves
**−2.8% in luminance** while the escape term inside it is **19.4%** wrong in red (`D`). And at
`τ = 0` the separated form is *exact*, because both integrands lose their `μ` dependence — so every
lossless check, every white-bed energy audit and every zero-absorption limit passes it untouched.
What sees it is a check at the file's own absorption with nothing averaged in it: the 400 000-photon
analog walk in `validate.py`, which attenuates each photon over its **own** `1/μ` and agrees with
the joint form to **0.15% at worst, under 0.1% in green and blue**. A second quadrature would have
shared the premise — the fourth way in [`11`](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one).

**The two forms this section replaced, priced on the same constants** (`D`, luminance weighted by
this file's own `SUN_COL`, `ρ_bed = 0.222 / 0.585 / 0.681`):

| Writing | `rho_water` | luminance | against the joint form |
|---|---|---|---|
| No up leg in the numerator at all | 0.0634 / 0.3074 / 0.4400 | 0.2569 | **+12.9%** |
| Up leg present, both integrals separated | 0.0343 / 0.2678 / 0.4279 | 0.2213 | −2.8% |
| **Joint integrals** | **0.0406 / 0.2745 / 0.4283** | **0.2275** | — |

The missing up leg is worth `1/⟨T⟩` — **1.846× in red**, 1.148 in green, 1.028 in blue — and it is
the easiest of the three to drop, because the round trip in the denominator *looks* like it has
already accounted for the column. The numerator must carry exactly **one** up leg and the
denominator exactly **one** round trip.

The renderer-facing consequence — that this is the shape of every water lookup table anyone is about
to bake — is [`12`](12-water-rendering.md#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them).

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
a pool's water column has **no body colour and can only subtract**: it takes red (`a` is 0.262/m over
the red band against 0.0102/m over the blue), and what survives *reads* as cyan. The band is not "the
wall colour without the cyan the water adds"; it is the same colour with nothing taken away.

### Which sampling of Pope & Fry, and why it is a decision rather than a rounding

`a(λ)` is a published curve; a renderer needs three numbers off it, and there are two defensible ways
to take them. The implementation now takes the second, and this is the reasoning.

```
(a) POINT SAMPLE at the three nominal wavelengths 620/545/460 nm
        a = (0.2755, 0.0511, 0.00979) m^-1
(b) BAND MEAN over the file's own Voronoi cells, 582.5-657.5 / 502.5-582.5 / 417.5-502.5 nm
        a = (0.26170, 0.052988, 0.010224) m^-1        <- what ships
```

Three reasons for (b), and none of them is that it looked better.

- **It is what the file's own doctrine already says.** `render.py` states, in the block immediately
  under the constant, that *a camera channel is a BAND, not a wavelength*; the bands are constructed
  there as the Voronoi cells of the three nominal wavelengths and they tile 417.5–657.5 nm with no
  gap and no overlap. Every *other* spectral quantity in the renderer is already sampled through
  them — `n(λ)` for the dispersion sweep, the per-ray caustic `eta`, the spectral Latin square. Taking
  `a` at a delta function while its neighbours are taken over a band is the inconsistency.
- **`a` is the quantity where the difference bites hardest.** It runs 0.0896 → 0.3400 m⁻¹ across the
  red band alone, so the point value and the band mean differ by **5.0%** there (3.7% green, 4.4%
  blue, and the red's sign is opposite to both). A curve that steep is exactly the case a three-delta
  quadrature handles worst, and the file already writes a page on that failure mode for silhouettes.
- **It is checkable both ways.** Both readings are computed from the same transcribed table in
  `validate.py`, and both rows are asserted, so the triple cannot drift towards either without a row
  moving.

The honest caveat, stated rather than buried: a band mean of `a` is still an approximation.
Beer–Lambert over a band is `−ln⟨exp(−a(λ)L)⟩`, not `⟨a⟩L`, and the two separate as `L` grows —
about 1% of the red channel's transmittance at the shipped 3.9 m path, more on the README's 8 m
underwater view. It is first-order right where a point sample is not even that, and the exact
treatment is a spectral integration this file does not do.

**The chapter's triple is not an alternative to it.** `12` quotes `a = (0.2644, 0.0565, 0.00922) m⁻¹`
at *its* sample points 610/550/450 nm. That is the same Pope & Fry table read at three different
wavelengths — same water, same measurement, two samplings of one curve — and presenting the pair as
competing values would be the same category error the blue defect below was. `validate.py` checks the
chapter's triple against the table at 610/550/450 and the implementation's against the band integral,
so the two are pinned separately to one source.

**What was wrong before.** `ABS = (0.2750, 0.0546, 0.0145)`. Red was Pope & Fry at 620 nm to 0.2%,
green was 6.9% high, and blue was `0.0145` — **Smith & Baker (1981) at 450 nm, exactly** — 48% above
Pope & Fry at 460 nm and 42% above the blue band mean. The wrong paper at the wrong wavelength, in a
project whose provenance appendix bans Smith & Baker for blue by name, because that era's blue
carries scattering from natural water. Two independent passes reached the same identification. The
regression guarding it is now written the other way round: blue must sit within 5% of the Pope & Fry
band mean *and* more than 10% away from every Smith & Baker value in 440–460 nm.

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
coefficients against Pope & Fry 1997 and Smith & Baker 1981, point-sampled and band-integrated, and
all of those rows now pass; the blue defect above cost the round-trip 1.7% over the shipped 3.92 m
path and the red 5.3% the other way, both now removed. **The dry-band regression itself still has no
test**; it is a measurement the frame makes, checked only against the prediction from the file's own
`a`.

**What the band DID buy, and it was not a test.** When the `1/n²` was applied (item 5 of *What did not
reproduce*), the question was whether `LINER_TINT`, the liner albedos and `EXPOSURE` had been
absorbing the missing factor — because if they had, applying it and re-fitting them would just move
the error. The band settles it with no free parameter, because it is the same pigment with **no water
path, no interface and no `n²`** between it and the eye: its radiance over its own irradiance is the
albedo, full stop. Measured `(0.271, 0.727, 0.835)` against this file's `0.74·LINER_TINT =
(0.222, 0.585, 0.681)` and chapter 12's mid-blue PVC `(0.24, 0.54, 0.70)` — inside 8%, where a
pigment carrying the factor would have to sit 78% out. So nothing was re-fitted, and the rendered
band moved by one sRGB level while the water beside it fell 0.83 stops.

**One caveat on the printed row, stated rather than arranged away.** The picture-side ratio (sunlit
floor over dry band, each divided by its own irradiance) does **not** close on
`T(θ_v)/n²·exp(−a·L)`, and it is not made to. Two things separate them: the floor pixel is not the
transmitted column alone — the reflected sky is ~6% of its luminance and the band has no sky term to
divide out against — and the two medians are not the same estimator, one being a per-point radiance
over a per-point irradiance and the other a median *picture* pixel over a median *map* irradiance,
which a skewed caustic net does not let commute. The row is a consistency check with a known sign.
What actually measures the absorption is the map row above it, which is exact.

---

## 11. The static-equilibrium bay

**Why.** `12`'s refraction cues all turn crests onto contours, and the cheapest field check on them
— "do the surf lines follow the curve of the bay" — is void on a straight shore, because a
shore-keyed ramp under a straight shoreline has straight contours and the crests arrive parallel to
them having done no work. Giving a scene a curved shore therefore has to be a *derivation*, not a
drawing, and the headland-bay literature supplies the form. What follows is the algebra, the one
member of the family that is genuinely derivable, and the impossibility result that says what a
curved bay actually requires.

### The condition

The CERC longshore transport closure (Komar & Inman 1970, and terrain-architect `12`'s own statement
of it) is

```
Q = K/(16 (s-1)(1-p) sqrt(gamma_b)) * sqrt(g) * H_b^(5/2) * sin(2 theta_loc)      [m^3/s]
```

with `s = rho_s/rho_w`, `p` the pore fraction, and `theta_loc` the angle between the wave orthogonal
at breaking and the **local** shore normal. The whole prefactor is positive and constant, so

```
Q = 0   <=>   sin(2 theta_loc) = 0   <=>   theta_loc = 0
```

**and the empirical coefficient `K` cannot reach the answer.** `K` sets the rate at which a shore
relaxes and nothing about where it relaxes to. That is worth stating because `K` is the one number
in this derivation that could have been tuned to make the result come out; the implementation
doubles it and checks the plan-form does not move, and separately checks that `Q` doubles exactly,
because either row alone is also consistent with `K` being ignored.

### The sign, which is the one thing a reader gets backwards

With `x` shoreward-positive and `y` alongshore, a shoreline `x = x_s(y)` has tangent
`t = (x_s', 1)/N`. Rotating by −90° gives `(1, −x_s')/N`, which points shoreward, so the shoreward
normal lies at `−phi_s` from the `+x` axis where `phi_s = atan(x_s')`. A wave travelling at `theta`
to `+x` therefore meets the shore at

```
theta_loc = theta + phi_s
```

### The impossibility result: plane crests admit only a straight equilibrium

Take plane offshore crests (one direction `theta_0`, everywhere) and contours that follow the shore.
Snell about the local normal is `sin(theta_b,loc) = (c_b/c_0)·sin(theta_0,loc)`. Since `c_b/c_0 > 0`,

```
theta_b,loc = 0   <=>   theta_0,loc = 0   <=>   phi_s = -theta_0
```

Refraction shrinks an obliquity; it never sends a non-zero one to zero. Integrating the constant
`phi_s`:

```
x_s(y) = x_ref - tan(theta_0) * (y - y_mid)
```

**A straight coast, rotated by the FULL deep-water obliquity** — not the breaking one. That
distinction is a factor-of-two-class trap of its own: rotating by the *breaking* angle (6.56° on the
reference scene, against `theta_0` = 20°) leaves 2.78° of residual obliquity and 43 % of the
straight coast's transport, and the implementation shipped that version first.

The consequence is the useful part. Any curvature makes `phi_s` vary, `theta_loc` can then be zero at
one station only, and **the transport goes up**. A curved static-equilibrium bay does not exist for a
plane-crest field. It exists only where the orthogonal **fans** alongshore, and the fan is the
sheltering headland's diffraction and refractive focusing — which is the term `12`'s
diffraction section says no ray model has. The geometry gives its size with no wave model in it at
all: the fan a stated shoreline requires is `psi(y) = -phi_s(y)`, and its alongshore range is the
swing the headland must supply. On the reference scene's bay that is **39.6°**.

### Why the logarithmic spiral, and which member is derived

Suppose the orthogonals radiate from a pole `D` (the diffraction point, or the virtual source the
fan converges on). Then the radius vector *is* the orthogonal and `theta_loc = 0` reads "shore normal
to the radius":

```
tangent . radius = 0   at every station   =>   a CIRCULAR ARC about D, exactly.
```

That is the derived member, `alpha = 90°`. Now let the orthogonal be rotated off the radius by a
**constant** `delta`. The shore normal is the radius rotated by `delta`, so the tangent makes the
constant angle `alpha = 90° - delta` with the radius, at every station. A curve whose tangent makes a
constant angle with the radius vector from a fixed pole is, by definition and uniquely, the
logarithmic spiral:

```
R(phi) = R_a * exp((phi - phi_a) * cot(alpha))
dP/dphi = R'(phi) u + R(phi) u_perp = R (cot(alpha) u + u_perp)
angle(dP/dphi, u) = atan(1/cot alpha) = alpha,  independent of phi.       QED
```

So the spiral is not a curve fitted to four coastlines; it is *the* curve of constant residual
obliquity, and the fit is what its **one** parameter absorbs. `delta` itself is **not** derivable
here and is marked `?`. Silvester's published `alpha` for real bays is 30–50°, i.e. `delta` = 40–60°,
which is an order above anything refraction leaves at the break point and is an empirical fit to a
different quantity; the implementation ships `delta = theta_b` as a declared choice and computes the
circle (`delta = 0`) beside it every run. On the reference scene the two differ by **0.9 %** in
indentation, which is why the `?` is reported rather than chased.

### Closing the pole: two equations, no freedom left

A log spiral has four freedoms — the pole `(D_x, D_y)`, the scale `R_a`, and the angular origin
`phi_a`. Two rock anchors `A1, A2` (the seaward-most shoreline in the outer quarter of each end of
the coastal loop's own plan-form) absorb `R_a` and `phi_a` outright and leave one condition on the
pole, because the spiral's similarity property is

```
ln(r2/r1) = cot(alpha) * (phi2 - phi1),      r_i = |A_i - D|,  phi_i = arg(A_i - D)
```

The second condition is Hsu & Evans' **downcoast control point**: the point at which the beach
becomes parallel to the incoming crests, i.e. its normal lies along the wave vector, i.e.

```
tangent(A2) . khat = 0,        khat = (cos theta_0, sin theta_0)
```

Two equations, two unknowns. Damped Newton on a 2×2 numerical Jacobian closes both to `< 1e-13`.
**The indentation is therefore an OUTPUT**, and so is the downcoast tangent's bearing, which is
recomputed from the sampled shoreline rather than from the condition and comes back at exactly
`−theta_0`.

**Two branches exist and only one is a bay.** A pole at infinity is always a root — a spiral with an
infinitely distant pole is a straight line, and the tangency condition then fixes its bearing, so
that branch *is* the rotated straight coast above. The bay is the **nearest** root, and the selection
rule has a statement behind it: the pole is the sheltering headland's diffraction point, and a pole
79 km offshore is not a headland. The solve is multi-start and both branches are reported.

### Where the residual goes

Firing the transport meter at the built bay under the fan its own pole implies gives
`Q_rms = 2.65e-2` m³/s over the spiral span against a **measured floor** of `1.78e-3` (the
closed-form zero-transport coast through the same solver): small, and about 15× the floor. Two
mechanisms, separated by measurement rather than by argument:

1. **The ramp is not concentric with the curve it is keyed to — 0.71°.** `d = A(x_s(y) − x)^(2/3)`
   has contours that are `x`-translates of the shoreline. Translates of a *concave* curve converge,
   so a ray arriving normal to the shoreline does not stay normal to the contours it crosses, and
   refraction returns some obliquity. Rebuilding the same circular bay with `d = A(R_s − r)^(2/3)`,
   `r` measured from the pole — concentric arcs, on which a radial ray is normal to every contour —
   removes exactly this much. Two beds, one shoreline, one incidence: the difference is attributable.
2. **The march meeting curvature — 1.46°.** A column-marched transform carries the ray's alongshore
   drift only through `∂k/∂y`. On *straight* contours at the same 20° obliquity the identical march
   leaves 0.20°; on concentric contours with exactly radial incidence it leaves 1.66°. The excess is
   the solver, not the physics, and it is named rather than absorbed into a tolerance.

### What this section does not close

- `delta`, the residual obliquity — `?`, bracketed by the circle.
- The **parabolic bay-shape equation** (Hsu & Evans 1989). Fifteen fitted quartic coefficients with
  no internal consistency check that would catch a wrong digit, and nothing in this container holds
  them. Writing them from memory would manufacture a citation, so the form is named and **not**
  implemented. Anyone with the paper should add it: its advantage over the spiral is precisely that
  it produces the straight downcoast tangent as part of one formula instead of as a join.
- The **fan itself**. The implementation supplies it as a stated per-row offshore direction radiating
  from the bay's own pole, which is a boundary condition and not a diffraction solve. A Sommerfeld /
  Penney–Price edge stamped at the headland tip would make the fan an output; that is the next wave's
  work and it is the same term `12`'s diffraction section prices.

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
| Meniscus profile (shape) | RK4 march of the Young–Laplace IVP, from the wall outward | 3 | pass (4×10⁻¹⁴ m) |
| Meniscus quadrature (`z` and `dx` jointly) | force balance `ρg∫z dx = σ cos θ_c`, at four contact angles | 1 | pass (0.003%) |
| Fillet excess projected area | telescoping identity `V_m z(φ*)`, both signs of `V_m`; 4000-ray brute-force march | 1, 3 | pass |
| The deposit: node weights, Fresnel split, kernel, fold | unit-radiance closure integrated back to the excess area | 3 | pass (2%) |
| Both terms → 0 as `a → 0` and as `θ_c → 90°` | forced limits, linear in each | 1 | pass |
| Reachability algebra `R(φ)·L`, `β = A − B` | literal reflection over 60 random `(V, L)`; constructed `(L+V)·t = 0` | 1 | pass (9×10⁻¹⁶) |
| Internal reflection off the fillet's underside | **refuted**: `f = η cos_i − cos_t < 0`, so `t_z < 0` identically; 323 400-sample scan, 0 hits | 1 | pass |
| Floating-body flotation (`β`, draught, waterline) | the cap re-integrated as a 20 000-node quadrature of `π r(z)² dz` — never forming the closed-form cap volume — and the line tension re-derived from **Keller's theorem** (the pull equals the weight of liquid the meniscus displaces) | 1, 3 | pass (2×10⁻⁴ rel.) |
| The fillet at a hull's contact angle (`φ_w = β`, not 90°) | the force balance and the projected-area identity re-run on the float's own table through the **shipped** `_menis_weights` | 1 | pass (0.00%) |
| The split condition `R(1 − sin(β+θ_w)) > z_w sin θ_w` | 396 `(β, θ_w)` pairs × 4800 rays through the shipped ray–sphere solve — no shared algebra | 3 | pass (and it **failed** the first version of the derivation, on 196 of 396) |
| The radiance the two columns read (`_env_menis`, the traced maps) | — | — | **no test** (stubbed for the closure row) |
| `W(k)`, `σ_w = 0.3748·fp`, `half_footprint = λ/2` | closed-form identities | 1 | pass |
| Separable evaluation vs direct sum | grid vs point path | 3 | pass |
| `C = JΣJᵀ`, `J = diag(−2, −2cos θ_v)` | 400k perturbed reflections | 3 | pass (1–2%) |
| Stretch `= 1/cos θ_v` | identity | 3 | pass |
| Exact Fresnel `R = (R_s + R_p)/2` as the base curve | `R(θ_B) = ((n²−1)/(n²+1))²/2` closed form; `R(0) = F0`; a separate evaluation over 0–90° | 1 | pass |
| `refract()`'s TIR branch | bisection on its own null return vs the angle `R` reaches 1 | 1 | pass |
| `n = 2/θ_s² − 1`, `Ω_sun`, `L_sun`, disc flux | closed-form identities | 1 | pass |
| Rayleigh aureole flux `= mτ_R/8` of the beam | identity; Hansen & Travis `τ_R`; sun colour to 10⁻³ | 1 | pass |
| `TIR_FRAC = 1 − 1/n²` | identity + 2M-sample cosine-weighted MC | 1, 3 | pass |
| Rectangle view factor `_sky_vf` | 400k-sample MC at three geometries | 3 | pass |
| **`TIR_VERT`** | `tir_vert(0) = ½` as a limit, cross-checked against `_ris_closure`'s own ½; quadrature and 4M-sample MC **of the arriving radiance** | 1, 3 | pass |
| Riser gather closure `= ½`, truncation | closed form + MC of the shipped weight | 1, 3 | pass |
| Stone/band gather (`ρ³cosφ·q/R⁴`) | — | — | **no test** |
| Caustic pass vs analytic `1/\|J\|` | 1-D sinusoid, below and past focus | 1 | pass (0.086%, folds to 0.38 mm) |
| `F = d(1−1/n)sk`; `0.25 = 1 − 1/n`; onset 0.70478 | bisection on `min\|J\|` | 1 | pass |
| Penumbra compression `cos i/(n cos t)`; 6.8 mm | differentiated Snell; traced slant | 1 | pass |
| Flat-surface degenerate case (offset, uniformity) | closed form | 1 | pass |
| Beer–Lambert composition, slant, monotonicity | identities | 1 | pass |
| `2E₃` itself | `2E₃(0) = 1` exactly; the `E_{n+1}` recurrence down to `E_1` by its own series — no quadrature node shared | 1, 3 | pass |
| **`T_esc`, `G_rt` and the closed series** | the lossless limit `R(θ_sun) + ρ_water(1, a=0) = 1` (shape only), **and** a 400k-photon analog walk at the file's own `ABS` (the legs) — 0.15% worst channel | 1, 3 | pass |
| The trap as the shipped pass carries it | priced, not asserted: `trap_gain(bounces=1, cone_only=True)` against the closed series | 1 | **info** — the deficit is real and open |
| Riser caustic read at the beam's continuation | — | — | **no test**; the stripe rms and the z/arc ratio are render-side diagnostics, not suite rows |
| Vertical face's window vs mirror split | the halves are arithmetic on `TIR_VERT` and `TIR_FRAC`, and both of those are guarded above; the partition identity `window + mirror = tir_vert(0) = ½` holds exactly, and `WALL_SKY == tir_vert(0)` is its own row | 1 | pass — but **no row asserts the split is what the renderer applies** |
| Snell's Jacobian `cos θ_a/(n² cos θ_w)` | the identity `∫ dΩ_a = 2π(1 − cos θ_c)`, which is what makes the window audit's percentages shares *of* something | 1 | pass (2.1213850054 vs 2.1213850054) |
| `air_world` returns sky / edge / sail / float in that order | four rays aimed by geometry at the four things above this water; the kinds are what the audit is binned on, so a wrong code is a wrong report | 1 | pass |
| The window audit's **shares** | — | — | **no test**: two estimators are run and reported side by side, and they measure two different questions (see the Jacobian section above). Neither is a guard on the other |
| The sail's underside radiance | — | — | **no test**, and this is the coverage case: it lands on **0** subsamples of the hero frame, so the picture cannot see it either. Derived, not guarded |
| `R_ext`, `R_int`, `a_wet` boundary conditions | quadrature; reciprocity; Egan & Hilgeman fit | 1, 3 | pass |
| `a(λ)` itself | Pope & Fry 1997 point-sampled *and* band-integrated; a Smith & Baker exclusion row | 2 | pass |
| Dry-band absorption regression | — | — | **no test** |

Also unguarded, and worth knowing before quoting any level from this material: the five-band
decomposition itself (`WIND_RMS`, `REVERB_RMS`, `JNEAR_RMS` are chosen, and the chapter's far-field
figures were read off the implementation, so they cannot confirm it); every material colour; the
tone map; and the whole camera pass. Cox & Munk can bracket the *total* slope and does — the basin's
total mss sits inside the `W = 0 … 1 m/s` band and the far-patch slope excess kurtosis sits inside
the −0.5…1.5 band on both axes — but nothing pins an individual band's level.

## What did not reproduce

Six checks recorded here disagreed with the implementation. **Four of the six are now closed in the
code** — items 1, 4, 5 and 6, the ones that were about the *model* rather than about a sentence
beside it — and every one of them is kept in full, because the mechanism by which a wrong number
survives a test suite is the transferable part, and deleting the record would throw exactly that
away. Each closed item now carries what it was, what closed it, and the guard that would have caught
it; where the guard is the more interesting half, that is said.

**Items 2 and 3 stay open**, and deliberately: both are comments in `wake.py` and `render.py` whose
prose overstates or mislabels a number the code gets right, and both sit inside blocks this round was
told not to touch. They are one-line corrections for whoever owns those blocks, not for this round.

A seventh disagreement, found while closing the four, is recorded after item 6 and is **open**. An
eighth, found in this pass, is recorded after it and is **closed by recomputation**: it is an
arithmetic slip in a write-up rather than a defect in the code.

1. **`TIR_VERT` — the vertical-face internal-reflection ratio.** *Now fixed; shipped value 0.885.*
   It shipped 0.563; the derivation stated beside it evaluates to 0.635; the correct value for a
   uniform Lambertian bed under a mirror is **0.885**. The stated derivation weights the receiver
   integral by the *emitted flux* density `cos t sin t`, which already contains the horizontal
   receiver's own cosine and so must not be carried into the vertical case; the shipped expression
   additionally had one `sin t` too many relative to that. The correct form is
   `(π/2 − θ_c + sinθ_c cosθ_c)/(π cos²θ_c)`, confirmed against a 4M-sample uniform-solid-angle
   Monte-Carlo (0.8858 ± 0.0004) and against the full-hemisphere limit, which it sends to exactly ½.
   **`validate.py`'s two failing rows expected the middle number**, so satisfying the suite would have
   replaced one wrong value with another — the test and the code were written from the same sentence,
   which is the general hazard of validating a derivation against a restatement of itself. What
   closed it was not a better estimator but a check with **no premise to share**: the `θ_c → 0` limit,
   which is forced to be ½ and which both wrong forms miss (0.239 and 0.318). Full algebra in
   [§7](#7-the-internal-reflection-integrals).
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
4. **`render.py`'s own header quoted `F0 = 0.0197`.** *Now fixed; the header quotes all three.*
   From the file's three IORs, `F0 = ((n−1)/(n+1))²` is `(0.02027, 0.02056, 0.02111)`; 0.0197 is what
   `n = 1.3265` would give, a number that appears nowhere else in the file. It was 3–7% low and it
   was a docstring, so nothing computed from it — but it is exactly the class of thing this project
   cleans up: a stated constant that no longer follows from the code beside it. `validate.py` already
   asserts `F0` against `IOR` to float round-off, so the pair cannot drift again in silence. The
   same round fixed the file's other cosmetic slip, `wrote pool.png` printed while writing
   `pool_final.png`.

5. **The transmitted column was missing the `1/n²` radiance compression.** *Now fixed; there is one
   function, `out_of_water`, and three call sites.* `water_shade` composed
   `out = F(θ_v)·L_sky + (1 − F(θ_v))·L_bed`, where `L_bed` is built by `shade()` as
   `albedo × irradiance` — an **in-water** radiance, since its irradiance is the beam already
   transmitted through the surface (`SUN_COL·cos_i·TSUN`) with the `1/π` carried by `SUN_COL`'s own
   convention. Radiance is not conserved across a refracting interface; `L/n²` is, because a
   pencil's étendue `n² dA dΩ` is. Leaving the water, therefore,

   ```
   L_air = T(theta_v) * L_water / n^2,      n^2 = 1.774 / 1.782 / 1.796 on this file's three IORs
   ```

   and the `/n²` was absent — 0.827 to 0.844 stops. It was a **relative** error between the two
   columns of the same pixel: the reflected sky term is air-side and correct, so the bed read ~1.78×
   bright against it, which is the one thing the spec-C reflected-vs-transmitted diagnostic exists to
   measure, and which no exposure could have absorbed. The internal return (`bedret`, `TIR_FRAC`) is
   *not* the missing factor — it is the light that failed to escape coming back to re-light the bed,
   and it is already in `L_bed`'s irradiance, on the other side of the division.

   **Why the suite did not have it.** Eleven rows covered the exact Fresnel equations, one of them
   a value an approximation cannot reach. Not one of them ever asked what happens to a *radiance*;
   they all asked what happens to a *ratio*, and a ratio is exactly where this factor cancels. The
   shape of the hole is the transferable part: an interface has two transports and the suite only
   knew about one of them.

   **What closed the calibration.** The stated reason for recording rather than fixing was that
   `LINER_TINT`, the liner albedos and `EXPOSURE` were fitted to a photograph with the factor absent
   and might be compensating for it, so applying the divisor and raising `EXPOSURE` to put the
   brightness back would install the error somewhere else. What breaks that circle is the dry liner
   band of §10: it is **the same pigment with no water path at all**, so it has no absorption, no
   interface and no `n²` anywhere between it and the eye, and its radiance over its own irradiance is
   a direct readout of the albedo. Measured on the frame it is `(0.271, 0.727, 0.835)`; the file's
   `0.74·LINER_TINT` is `(0.222, 0.585, 0.681)`; chapter 12's mid-blue PVC liner is
   `(0.24, 0.54, 0.70)`. **−7 / +8 / −3 per cent.** A pigment carrying a missing factor of 1.78 would
   have to sit 78% off a published PVC. So the factor was never in the pigment, and neither
   `LINER_TINT` nor `EXPOSURE` moved. The rendered dry band confirms it from the other side: it moved
   by **one sRGB level**, (44,151,172) → (45,153,173), while the water beside it fell 0.83 stops.

   **One constant did move, and it was the same factor written by hand.** `WBOUNCE`, the pool's
   upwelling radiance onto the stone at its edge, led with a bare `0.5`. That is the *diffuse* form
   of this transport — `1 − R_int = (1 − R_ext)/n² = (0.5263, 0.5238, 0.5193)`, which the file already
   computes for the wet-liner term of §10 — rounded down by 4.5% with no derivation beside it. So the
   file **already carried the `1/n²` on one route out of the surface** while the camera's route went
   without: two exits from one interface disagreeing by `n²`, and nothing in the file compared them.
   `WBOUNCE` now takes `T_OUT_DIFFUSE` and rises 4.8%.

   **The guard, which is the part that could not be written from the derivation.** Three rows:

   - **Walsh's relation**, `n²(1 − R_int) = 1 − R_ext`, with *both* sides quadratured inside
     `validate.py` — the internal one the long way, through the whole total-internal-reflection cone
     rather than by reciprocity. It pins the **exponent**, not merely the presence of a factor: at
     `n¹` the two sides differ by 25%, at `n³` by 33%.
   - **A closed energy audit.** A pool with a perfect white Lambertian bed and no absorption must
     have an apparent albedo of **exactly 1**. The right-hand side of that row is the number 1 and no
     constant of `render.py` enters it. Composed through `out_of_water` it is 1; composed as the file
     shipped, **1.723 / 1.730 / 1.742**; composed with `1/n`, **1.310**.
   - **The same audit off unity against `wet_albedo`**, which reaches the same physical quantity by
     summing a trapped geometric series and is itself guarded against the Egan & Hilgeman fit.

   **And the image is darker, which is the answer.** Open water goes (81,192,204) → (56,155,170)
   sRGB, the sunlit floor (74,189,205) → (52,151,171), the far water's mean encoded luminance
   152.7 → 131.5. Nothing was raised to put it back.

6. **The submerged walls stood 20 mm outside the surface they met.** *Now fixed; the four planes are
   `XW0, XW1, YW0, YW1`, at `s = SLIP`.* Found while tracing the meniscus's transmitted column, and
   closed in the same round as item 5 because both of them make the dry-band regression of §10 be
   re-read.

   The water's plan boundary — the vertical face carrying the liner band, the line the height field
   cliffs at, the line the meniscus climbs — stands at `s = SLIP = −0.020`. `scene_hit` put the four
   submerged walls on the plan rectangle, `s = 0`, which is the coping's bedding line and not a
   surface anything can see. So a refracted camera ray travelled 20 mm further before it met the wall
   than the geometry above it said, and landed correspondingly deeper: about **5 mm lower on the
   liner**, against a wall map whose own coping-shade term has a 55 mm scale at the top. Everywhere
   else in the basin 5 mm out of 1.40 m is nothing; at the waterline it is the whole gradient. It
   very nearly cancelled inside the meniscus's own subtraction — the fillet's traced ray and the flat
   baseline's are both displaced by it, and what is added is the difference — which is why the term
   was built on `scene_hit` as it stood.

   Two consequences came with the move and neither was reachable before it:

   - **A backward root is a miss.** The laid-stone wobble lets a water hit sit up to ~7 mm outside
     the wall plane it belongs to, and such a ray travels *away* from that plane, so it never meets
     it. With the walls on the rectangle that root was zero; with them moved in it is negative, and
     unguarded it wins the `argmin` and traces backwards through the eye.
   - **The caustic launch grid spans the rectangle**, whose outer 20 mm is coping rather than water,
     so 1.5% of the sun rays were being launched off stone. It never showed while a wall stood at
     `t = 0` under them. Now masked on `pool_sdf < SLIP`.

   Measured on the fillet's own traced column: on the north wall at *x* = 1.40 m the transmitted rays
   used to land between −118.8 and −1.1 mm of the still line over 29–175 mm of water; they now land
   between −45.7 and +3.8 mm over 0–67 mm. On the west wall, 20.4–44 mm of water becomes 0–17 mm.

   **The guard is two constructions of one surface, plus a march.** `scene_hit` does not call
   `pool_sdf` and never has, so `validate.py` fires 6000 rays and asserts that every wall hit lands
   on `pool_sdf == SLIP` to float round-off — on the planes this shipped with, that row reads 0.020
   exactly — that no traced segment leaves the boundary, and, independently, that a 1 mm march of the
   bed height field finds the same first hit to within its own step.

7. **The `0.30` on every above-water direct-sun term. OPEN.** Found while closing the six above.
   `_stone` and `liner_band` both write the direct beam as `SUN_COL·(N·L·vis + …)·0.30`, while
   `shade()` — the bed, the walls, the treads — writes it as `SUN_COL·cos_i·TSUN·cau` with no such
   factor. `SUN_COL` is `E/π` by the file's own stated convention, which `validate.py` asserts as
   `E_SUN == π·SUN_COL`, so a Lambertian facet in this beam has radiance `ρ·SUN_COL·(N·L)` and the
   stone is being given **0.30 of it — 1.74 stops under** the beam that lights the bed at full
   strength. `SKY_DECK`'s own `SKY_AMB·0.30 + SUN_COL·0.075` carries a derivation in the comment
   above it; this `0.30` carries none anywhere in the file.

   Left open on purpose. It is a **calibration** question and the reference is a photograph this
   round does not have, so moving it would be the compensating move that item 5 refused. Its blast
   radius is the whole above-water half — coping, paving, freeboard band, and the `WBOUNCE`/`SKY_DECK`
   balance — and it is entangled with albedos already marked `?` as visual readings. And the frame
   moved underneath it twice in this round: the water fell 0.83 stops and two of the four copings
   gained their direct sun, so whatever balance this constant was dialled against no longer holds.
   What is not in doubt is that two receivers in one frame are being given the same beam at a ratio
   of 3.33, with a derivation on one side and nothing on the other.

8. **An inflatable ring's draught.** *A write-up figure; the code never used it.* The argument that
   an air-filled ring is the wrong instrument for a waterline is right and the number attached to it
   is not. With tube radius `r = 90 mm` and skin `t = 0.25 mm`, the shell fraction of a **torus** is
   `2t/r`, so `ρ_eff = ρ_PVC·2t/r + ρ_air = 8.42 kg/m³` and the submerged volume fraction is
   **0.842%** — both of which reproduce. The draught that follows does not: for a circular section a
   submerged **area** fraction of 0.842% needs a half-angle of `α = 0.3438 rad`, i.e.
   `d = r(1 − cos α) =` **5.27 mm**, not the 9 mm quoted. (For a floating torus the two fractions are
   the same number: the bottom segment is symmetric about the tube's own axis, so Pappus gives
   `V_sub/V = A_sub/A` exactly.) 9 mm would need `ρ_eff = 18.7 kg/m³`. The likely origin is visible
   in the companion figure, which **does** reproduce: a beach ball of `R = 180 mm` and the same skin
   has shell fraction `3t/R`, hence `ρ_eff = 6.62 kg/m³`, 0.663% and a draught of **17.2 mm** against
   the quoted 17 mm — so the sphere's `3t/R` appears to have been carried onto the tube, where the
   right factor is `2t/r`. The conclusion is unaffected and in fact strengthened: at 5.3 mm of
   draught the ring's own meniscus climbs **0.93 mm**, **17.7%** of it, so a waterline reading on an
   inflatable is a surface-tension measurement wearing a buoyancy label. *(`D`, all four numbers
   recomputed here; the method rule this belongs to is
   [`11`](11-verification-failures.md#pick-instruments-whose-parameters-someone-else-has-fixed).)*

## Three more, closed in the same round, that this file did not carry

They belong to `render.py`'s own README rather than to a derivation, but the record is one record:

- **The near-wall fold (`Vm < 0`) is now enforced rather than bounded in prose.** `_menis_weights`
  priced it at `|Vm|·h`, at most 3.9 mm of projected area per metre of waterline and signed negative,
  and observed that this frame never reaches it. `meniscus` now takes `guard=True` on every path that
  draws a pixel and raises the moment a selected ray has `Vm < 0`; `_menis_probe`, which deliberately
  walks the east and south waterlines to *report* the bound, is the one caller that passes
  `guard=False`. `validate.py` holds both halves — a north-wall configuration renders, an east-wall
  one is refused.
- **The wall map ran out above `z = 0`.** The fillet's steeper facets aim the transmitted ray 1–4 mm
  above the still line and `sample` clamped that to the map's top row. The bound is analytic: a
  refracted camera ray descends everywhere (`t_z < 0` identically — the same algebra that refutes the
  underside term in §3), so a ray launched at most `MENIS_H` above the still line can only land below
  it. The maps now run to `WTOP = MENIS_H = 3.85 mm`, one texel row out of 340, and a 128 304-hit
  march of the whole fan asserts the highest landing is inside it — two-sided, so a short map fails
  high and a bound nothing reaches fails low.
- **`sun_vis` applied `coping_vis` to stone.** `coping_vis` is a water-surface term and on a stone
  point it returns 0 for every side whose outward normal has a positive component toward the sun, so
  the north and west copings and paving got no direct sun at all. Stone now takes `stone_vis`, which
  is the sail alone, and the guard is a 2 mm shadow march of the real height field from 672 points on
  all four copings.
