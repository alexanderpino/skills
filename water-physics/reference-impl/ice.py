"""Ice: why it is not frozen water, optically, and what actually sets its colour.

THE CATEGORY ERROR THIS FILE EXISTS TO REFUTE. Ice rendered as "water with a
blue tint and a colder roughness" is the `waterColor` mistake of chapter 12 in a
different coat. Two things are wrong with it and they pull in opposite
directions, which is why tuning never converges:

  1. ICE'S ABSORPTION SPECTRUM IS A DIFFERENT SHAPE, not a scaled copy. At this
     project's own band points ice absorbs HALF the red, an IDENTICAL amount of
     green (to 1 %), and a QUARTER of the blue. Red:blue selectivity is 55.0
     against water's 25.6 -- more than twice as steep across the visible.
  2. THE COLOUR IS NOT A PATH INTEGRAL AT ALL. In clear water the colour is
     `exp(-a d)` along a path, and it vanishes when the path does. In glacier
     ice the light is SCATTERED by bubbles and grain boundaries long before it
     has travelled `1/a`, so what reaches the eye is a diffuse return governed
     by the RATIO of absorption to scattering -- and a ratio does not vanish
     when the slab gets thin, it saturates.

So the doctrine transfers with one substitution: **for water the colour is the
path; for ice the colour is `K/S`**, and the bubbles set `S`. Lake ice with few
bubbles reads nearly as a clear dielectric; glacier ice with many reads
saturated blue over a metre where water would need tens.

DATA PROVENANCE. `n` and `k` are read from Warren & Brandt (2008)'s tabulation
at this project's own three band points, fetched 2026-08 rather than recalled.
Everything else here is derived from them.
"""
import numpy as np

import optics as OPT

# --------------------------------------------------------------- the constants
# Warren, S. G. & Brandt, R. E. (2008), "Optical constants of ice from the
# ultraviolet to the microwave: A revised compilation", J. Geophys. Res.
# Atmospheres 113, D14220, doi:10.1029/2007JD009744. Tabulated at -7 C.
# `P`, values taken from the published ASCII table at the three wavelengths
# this project samples water at, so the two are comparable term by term.
LAM_NM = np.array([610.0, 550.0, 450.0])          # the band points, nm
IOR_ICE = np.array([1.3091, 1.3110, 1.3157])      # real index at those points
K_ICE = np.array([6.890e-9, 2.289e-9, 9.239e-11])  # imaginary index


def absorption_from_k(k, lam_m):
    """The absorption coefficient implied by an imaginary refractive index.

    `a = 4 pi k / lambda`, the standard relation between the imaginary part of
    the index and the Beer-Lambert coefficient. Derived here rather than
    tabulated so that changing the wavelength triple changes the answer.
    """
    return 4.0 * np.pi * np.asarray(k, float) / np.asarray(lam_m, float)


ABS_ICE = absorption_from_k(K_ICE, LAM_NM * 1e-9)   # (0.1419, 0.0523, 0.00258)


def selectivity(a):
    """Red-to-blue absorption ratio: how steep a spectrum is across the visible.

    ONE NUMBER THAT SEPARATES ICE FROM WATER, and it is the reason a glacier is
    a more saturated blue than deep water at any path length. Water 25.6, ice
    55.0 -- ice is 2.15x the spectral selectivity, so the same number of
    absorption lengths removes far more red relative to blue.
    """
    a = np.asarray(a, float)
    return float(a[0] / a[2])


# ------------------------------------------------------------ the interface
def fresnel_normal(n):
    """Normal-incidence reflectance of an air/dielectric interface.

    `((n-1)/(n+1))**2`. Ice's 1.3091-1.3157 against water's 1.3320-1.3400 is a
    small shift and it moves R_ext by about 6 % relative -- worth having exact
    because the same constant appears in every specular term, but it is NOT
    where the appearance difference comes from. That is the point of computing
    it: to show the interface is nearly the same and the interior is not.
    """
    n = np.asarray(n, float)
    return ((n - 1.0) / (n + 1.0)) ** 2


def critical_angle(n):
    """`asin(1/n)`, the internal cone's half-angle."""
    return np.arcsin(1.0 / np.asarray(n, float))


# ------------------------------------------------ the scattering-dominated slab
def bubble_scattering(radius_m, number_density, q_ext=2.0):
    """Scattering coefficient of a bubbly medium, geometric-optics limit.

    `S = n * Q * pi r^2`, the number density times the extinction cross-section.
    `Q -> 2` is the large-particle limit (the extinction paradox: a sphere large
    against the wavelength removes twice its geometric cross-section), which is
    the right limit here -- glacier bubbles run tens to hundreds of microns
    against 0.5 um light.

    ⚠️ THIS IS THE ONE KNOB THAT SETS THE APPEARANCE, and it is a property of
    the ice's history rather than of ice: firn traps air, compression shrinks
    and eventually dissolves it, so old deep ice is clearer than young ice and
    reads bluer for that reason as well as for its depth.
    """
    r = np.asarray(radius_m, float)
    return np.asarray(number_density, float) * float(q_ext) * np.pi * r * r


def km_reflectance_infinite(K, S):
    """Kubelka-Munk diffuse reflectance of a SEMI-INFINITE scattering slab.

    `R_inf = 1 + K/S - sqrt((K/S)^2 + 2 K/S)`.

    THE FORM IS THE FINDING. `R_inf` depends on `K` and `S` only through their
    RATIO, so a semi-infinite slab of ice has a colour that does not depend on
    how deep it is -- which is exactly the opposite of clear water, whose colour
    is nothing but depth. That is why a crevasse reads the same blue from its
    lip as from ten metres down, and why "make it deeper" is not the control a
    renderer reaches for.
    """
    K = np.asarray(K, float)
    S = np.maximum(np.asarray(S, float), 1e-300)
    r = K / S
    return 1.0 + r - np.sqrt(r * r + 2.0 * r)


def km_ratio_from_reflectance(R):
    """The inverse: `K/S = (1-R)^2 / (2R)`. Used to read a photograph."""
    R = np.clip(np.asarray(R, float), 1e-12, 1.0 - 1e-12)
    return (1.0 - R) ** 2 / (2.0 * R)


def path_amplification(K, S):
    """How many times longer the diffuse path is than one absorption length.

    A SCATTERING MEDIUM MULTIPLIES THE PATH, and this is the second half of why
    ice is blue over a metre where water needs tens. Photons random-walk before
    they escape, so the mean path travelled is longer than the slab is thick.
    Taken here as the ratio of the absorptance a diffuse slab actually shows to
    the absorptance a single straight pass would give, in the limit where the
    slab is thick enough to be semi-infinite.

    Returned as a dimensionless factor per channel; it is largest exactly where
    absorption is weakest, which is the blue -- so the amplification is itself
    spectrally selective and works in the same direction as the spectrum.
    """
    R = km_reflectance_infinite(K, S)
    # absorbed share, against the share one transport mean free path would take
    absorbed = 1.0 - R
    single = 1.0 - np.exp(-np.asarray(K, float) / np.maximum(
        np.asarray(S, float), 1e-300))
    return absorbed / np.maximum(single, 1e-300)


# ------------------------------------------------------------- ice over water
def layered_reflectance(R_ice, T_ice, R_water):
    """Ice sheet over water: the geometric series, once.

    `R = R_ice + T_ice^2 R_water / (1 - R_ice R_water)`. The same interreflection
    sum chapter 12 uses for a pool's trapped light, applied one layer up. It
    matters because a frozen lake is NOT an opaque white lid: thin clear ice
    reads as the dark water beneath with a specular sheet on top, and the
    transition to white is the bubble density crossing the point where `T_ice`
    collapses -- not a separate material.
    """
    Ri = np.asarray(R_ice, float)
    Ti = np.asarray(T_ice, float)
    Rw = np.asarray(R_water, float)
    return Ri + Ti * Ti * Rw / (1.0 - Ri * Rw)


def compare_with_water():
    """The table this file exists to produce, computed rather than quoted."""
    aw = np.asarray(OPT.ABS, float)
    return dict(lam_nm=LAM_NM, n_ice=IOR_ICE, a_ice=ABS_ICE, a_water=aw,
                ratio_water_over_ice=aw / ABS_ICE,
                sel_ice=selectivity(ABS_ICE), sel_water=selectivity(aw))
