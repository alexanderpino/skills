"""Thin-film interference: the one water appearance driven by phase.

WHY IT NEEDS ITS OWN FILE. Every other colour in this skill comes from
absorption, scattering or Fresnel. An oil sheen comes from INTERFERENCE -- two
reflections separated by a film thinner than the coherence length, adding with
a phase difference that depends on wavelength and angle. None of this skill's
machinery reaches it, and no amount of tinting reproduces it, because the
signature is that the hue CHANGES WITH VIEWING ANGLE (goniochromatism) while a
tint does not.

⚠️ AND IT LANDS ON A TRAP THIS SKILL ALREADY NAMES. The interference term
oscillates in `1/lambda`, so evaluating it at three RGB sample points ALIASES:
past a few hundred nanometres of film the true spectrum has more oscillations
than three samples can represent, and the rendered hue becomes a function of
which three wavelengths you happened to pick. That is exactly
"a channel is a band, not a wavelength" at its sharpest, and it is why the
production answer pre-integrates the spectral response analytically rather than
sampling it.

SOURCE. Belcour, L. & Barla, P. (2017), "A Practical Extension to Microfacet
Theory for the Modeling of Varying Iridescence", ACM TOG 36(4) (SIGGRAPH),
doi:10.1145/3072959.3073620 (`P`) -- the production formulation, which works
over a rough base layer and pre-integrates spectrally so RGB and spectral
renderers agree. This file derives the underlying Airy summation and MEASURES
the aliasing that motivates it; it does not reimplement their model.
"""
import numpy as np

N_AIR = 1.0
N_OIL = 1.47          # `P`, typical mineral/crude oil in the visible
N_WATER = 1.334


def snell_cos(n_i, n_t, cos_i):
    """`cos theta_t` from Snell, or NaN past total internal reflection."""
    s_i = np.sqrt(np.maximum(1.0 - np.asarray(cos_i, float) ** 2, 0.0))
    s_t = np.asarray(n_i, float) / np.asarray(n_t, float) * s_i
    return np.sqrt(np.maximum(1.0 - s_t ** 2, 0.0))


def fresnel_rs_rp(n_i, n_t, cos_i):
    """Amplitude reflection coefficients, s and p. Signed -- the sign IS a phase.

    ⚠️ THE SIGN CANNOT BE DISCARDED HERE. Everywhere else in this skill Fresnel
    appears as an intensity `|r|^2` and the sign is irrelevant. In a thin film
    the sign is a phase shift of pi, and dropping it inverts the interference:
    the wavelengths that should cancel reinforce, and the colour comes out
    complementary. A sheen that looks "right but wrong colour" is usually this.
    """
    ci = np.asarray(cos_i, float)
    ct = snell_cos(n_i, n_t, ci)
    ni, nt = np.asarray(n_i, float), np.asarray(n_t, float)
    rs = (ni * ci - nt * ct) / (ni * ci + nt * ct)
    rp = (nt * ci - ni * ct) / (nt * ci + ni * ct)
    return rs, rp


def phase_delay(n_film, thickness_m, cos_t, lam_m):
    """Round-trip phase through the film: `4 pi n d cos(theta_t) / lambda`.

    The factor is FOUR pi and not two: the light crosses the film twice. The
    `cos(theta_t)` is what makes the hue swing with angle, and it is the whole
    visual signature -- at grazing the optical path shortens, the fringes shift
    to longer wavelengths, and the sheen runs through its colour sequence.
    """
    return (4.0 * np.pi * np.asarray(n_film, float)
            * np.asarray(thickness_m, float) * np.asarray(cos_t, float)
            / np.asarray(lam_m, float))


def airy_reflectance(lam_m, thickness_m, cos_i, n_out=N_AIR, n_film=N_OIL,
                     n_sub=N_WATER):
    """Reflectance of a single film on a substrate, summed over all bounces.

    The Airy formula, per polarisation:

        `R = |r01 + r12 e^{-i delta}|^2 / |1 + r01 r12 e^{-i delta}|^2`

    which is the same interreflection geometric series chapter 12 sums for a
    pool's trapped light, done in AMPLITUDE instead of intensity -- and that is
    the only difference that matters. Summing intensities loses the phase and
    gives a smooth, colourless result; summing amplitudes keeps it and gives
    the fringes.
    """
    lam = np.asarray(lam_m, float)
    ci = np.asarray(cos_i, float)
    ct1 = snell_cos(n_out, n_film, ci)
    rs01, rp01 = fresnel_rs_rp(n_out, n_film, ci)
    rs12, rp12 = fresnel_rs_rp(n_film, n_sub, ct1)
    d = phase_delay(n_film, thickness_m, ct1, lam)
    e = np.exp(-1j * d)
    out = []
    for r01, r12 in ((rs01, rs12), (rp01, rp12)):
        num = r01 + r12 * e
        den = 1.0 + r01 * r12 * e
        out.append(np.abs(num / den) ** 2)
    return 0.5 * (out[0] + out[1])


def fringe_spacing_nm(n_film, thickness_m, cos_t, lam_m):
    """Wavelength separation between adjacent interference maxima.

    `dlambda ~ lambda^2 / (2 n d cos)`. THE NUMBER THAT DECIDES WHETHER RGB
    SAMPLING WORKS. When the spacing is wide against the visible band, three
    samples describe the spectrum; when it is narrow, they alias. This function
    is what turns "use a spectral renderer" from advice into a threshold.
    """
    lam = np.asarray(lam_m, float)
    return lam ** 2 / (2.0 * np.asarray(n_film, float)
                       * np.asarray(thickness_m, float)
                       * np.asarray(cos_t, float))


def rgb_aliasing_error(thickness_m, cos_i, n_bands=3, n_ref=401,
                       lam_lo=380e-9, lam_hi=730e-9, **kw):
    """How far three-sample RGB is from the band-integrated truth.

    MEASURED RATHER THAN WARNED ABOUT. Integrates the Airy reflectance over the
    visible band at `n_ref` wavelengths -- the reference -- and against
    `n_bands` point samples, and returns the relative error of the sampled
    answer. It grows with film thickness because the fringes get denser, which
    is the statement the chapter needs and the reason the production model
    pre-integrates.

    Returns `(error, fringes_across_band)` so the error can be read against the
    cause rather than as a bare number.
    """
    lam_ref = np.linspace(lam_lo, lam_hi, int(n_ref))
    r_ref = airy_reflectance(lam_ref, thickness_m, cos_i, **kw).mean()
    lam_s = np.linspace(lam_lo, lam_hi, int(n_bands) * 2 + 1)[1::2]
    r_s = airy_reflectance(lam_s, thickness_m, cos_i, **kw).mean()
    ct = snell_cos(kw.get('n_out', N_AIR), kw.get('n_film', N_OIL), cos_i)
    mid = 0.5 * (lam_lo + lam_hi)
    spacing = fringe_spacing_nm(kw.get('n_film', N_OIL), thickness_m, ct, mid)
    return abs(r_s - r_ref) / max(r_ref, 1e-12), float((lam_hi - lam_lo) / spacing)
