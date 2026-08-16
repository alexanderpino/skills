"""The exit-transport LUT, baked both ways, so the difference can be measured.

This is the code half of `12-water-rendering.md` section *Attenuation and escape
do not factorise, and a LUT is where you will separate them* -- the chapter's
sharpest real-time claim and, before this file, the one with no code behind it.
The claim is about a PRE-COMPUTATION, and the offline reference cannot test it
because the offline reference never pre-computes anything: it evaluates the
integral at the depth in front of it, every time. A LUT is the only place the
two factors can be separated, so a LUT is the only place the error exists.

NOTHING HERE IS A SECOND IMPLEMENTATION OF THE PHYSICS. Every integral comes
from `optics.py` across an import -- `slab_esc`, `slab_trap`, `_e3`, `R_INT`,
`T_OUT_DIFFUSE`, `ABS`. This file only decides WHERE THE MULTIPLICATION HAPPENS:
inside the integral (joint) or outside it (factorised). That is the whole
content of the claim and it is the whole content of this file.

    T_esc(tau) = INT_0^1 2 mu exp(  -tau/mu) (1 - R_int(mu)) dmu     # optics.slab_esc
    G_rt (tau) = INT_0^1 2 mu exp(-2 tau/mu)      R_int(mu)  dmu     # optics.slab_trap

THE TWO SEPARATED FORMS, AND THE FINDING THAT THERE ARE TWO. The chapter names
one separated form for the escape leg and it is unambiguous:

    T_esc_sep(tau) = 2E_3(tau) * (1 - R_int)          # a depth table x a constant

For the ROUND TRIP the chapter is silent about which depth the table is read at,
and its own two blocks answer differently. Both are things a table-builder
actually writes, and they are NOT the same number:

    SEP_2TAU : 2E_3(2 tau) * R_int      -- one table, read at the round-trip
                                           optical depth. The direct analogue of
                                           the escape leg, and what the chapter's
                                           SCALING TABLE (tau = 0.05 .. 2.00)
                                           reproduces to 0.3 pp.
    SEP_SQ   : 2E_3(tau)^2 * R_int      -- up leg times down leg times a mirror,
                                           the product of the means taken TWICE.
                                           What the chapter's 1.40 m POOL TABLE
                                           reproduces to 0.2 pp.

Both are baked here and both are reported, per band, in both ratio conventions,
because the four numbers that result are the four numbers this project has
already disagreed with itself about. See README.md, section `The 30%`.

The half-texel discipline is `12`'s *Format, precision, and the bug everyone
ships once*, and it is implemented here twice on purpose -- correctly in
`fetch`, and wrong in `fetch_naive` -- so the suite has something to measure
instead of something to assert.
"""
import sys as _sys
import os as _os

import numpy as np

# The physics is IMPORTED. `reference-impl` is the owner of every constant below
# and this file adds none of its own.
_REF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                     '..', 'reference-impl')
if _REF not in _sys.path:
    _sys.path.insert(0, _REF)

import optics as OPT                                            # noqa: E402


# --------------------------------------------------------------- the bakes
# TAU_MAX. The table's domain has to be justified, not chosen: the chapter's own
# warning is that a table fitted to one body of water is a bake. The domain here
# is stated in OPTICAL DEPTH, which is the nondimensionalisation the chapter asks
# for, so the same table serves any (a, d) pair whose product lands inside it.
# 1.0 covers this project's pool (tau_red = 0.3664 at its deepest, 1.40 m) with
# 2.7x of headroom, and covers the raster scene's 3.00 m shelf (tau_red = 0.785).
# A body that needs more is a different table and the suite says so: `clamp_frac`
# reports the share of a frame's pixels that saturate the domain.
TAU_MAX = 1.0
N_TEXELS = 64          # see `Interpolation error` in the README: 64 texels puts
                       # the bilinear error two orders below the factorisation
                       # error this table exists to expose, which is the only
                       # bar it has to clear.


def _tau_grid(n, tau_max=TAU_MAX):
    """Texel CENTRES for an n-texel table over [0, tau_max].

    The endpoints of the domain fall half a texel outside the outermost centres
    and that is not a defect -- it is what the half-texel remap in `fetch`
    exists to handle. Building the table on `linspace(0, tau_max, n)` instead
    (centres at the endpoints) is the other half of the same bug: it silently
    changes what the table means, and then a correct sampler reads it wrong."""
    return tau_max * (np.arange(n) + 0.5) / n


def bake_joint(n=N_TEXELS, tau_max=TAU_MAX):
    """The chapter's prescription: `Store T_esc[tau] and G_rt[tau] instead --
    one table, one fetch, two channels, identical cost.`

    Returns (tau_centres, table) with table[i] = [[T_esc], [G_rt]] per channel,
    shape (n, 2, 3). Both integrals come from `optics.py`; the only thing done
    here is to call them at a unit depth with the absorption set to `tau`, which
    is the nondimensionalisation -- `slab_esc` only ever sees the product."""
    taus = _tau_grid(n, tau_max)
    tab = np.empty((n, 2, 3))
    for i, t in enumerate(taus):
        a = np.array([t, t, t])           # tau = a * dep with dep = 1
        tab[i, 0] = OPT.slab_esc(1.0, a)
        tab[i, 1] = OPT.slab_trap(1.0, a)
    return taus, tab


def bake_factorised(n=N_TEXELS, tau_max=TAU_MAX):
    """The separated pair, as a table-builder writes it: ONE depth-indexed
    absorption table, and the two diffuse Fresnel constants beside it as
    uniforms. Returns (tau_centres, T_diff_tab, T_diff_2tau_tab) where

        T_diff_tab[i]      = 2E_3(tau_i)         -- the diffuse slab transmittance
        T_diff_2tau_tab[i] = 2E_3(2 tau_i)       -- the same table read at 2 tau

    Both are channel-independent -- E_3 is a function of optical depth alone --
    which is exactly the argument that makes the split look free: one scalar
    table plus two constants, against six channels of joint table. The constants
    are `optics.T_OUT_DIFFUSE` (= 1 - R_int) and `optics.R_INT`, unchanged."""
    taus = _tau_grid(n, tau_max)
    td = OPT._e3(taus)
    td2 = OPT._e3(2.0 * taus)
    return taus, td, td2


# ------------------------------------------------------------ the sampler
def fetch(tab, tau, tau_max=TAU_MAX):
    """Bilinear fetch with the half-texel remap done right.

    A table of n texels over [0, tau_max] has its centres at tau_max*(i+.5)/n.
    A query at tau lands at the continuous texel coordinate

        x = n * tau / tau_max - 0.5

    which is negative for tau below the first centre and above n-1 for tau above
    the last. THE CLAMP IS PART OF THE CONTRACT, not a guard bolted on: a
    hardware sampler in CLAMP_TO_EDGE addressing does exactly this, and a table
    that is only correct in its interior is a table with two wrong endpoints --
    `12`'s `most-shipped LUT bug there is`. `fetch_naive` below is the version
    without it, kept so the suite can measure the difference rather than assert
    that it matters."""
    tab = np.asarray(tab)
    x = np.asarray(tau, float) * (tab.shape[0] / tau_max) - 0.5
    x = np.clip(x, 0.0, tab.shape[0] - 1.0)
    i0 = np.floor(x).astype(np.int64)
    i1 = np.minimum(i0 + 1, tab.shape[0] - 1)
    f = (x - i0).reshape(x.shape + (1,) * (tab.ndim - 1))
    return tab[i0] * (1.0 - f) + tab[i1] * f


def fetch_naive(tab, tau, tau_max=TAU_MAX):
    """The same fetch WITHOUT the half-texel remap: `u = tau / tau_max` straight
    into an n-wide table, which is what `texture(lut, tau/tauMax)` compiles to
    when the table was built on texel centres and nobody thought about it. The
    whole table is shifted by half a texel; the error is largest where the
    curvature is, i.e. at tau = 0, and it does not vanish with n -- it is
    O(f'(tau) * tau_max/n), first order, against the correct fetch's second."""
    tab = np.asarray(tab)
    x = np.asarray(tau, float) * (tab.shape[0] - 1) / tau_max
    x = np.clip(x, 0.0, tab.shape[0] - 1.0)
    i0 = np.floor(x).astype(np.int64)
    i1 = np.minimum(i0 + 1, tab.shape[0] - 1)
    f = (x - i0).reshape(x.shape + (1,) * (tab.ndim - 1))
    return tab[i0] * (1.0 - f) + tab[i1] * f


# ------------------------------------------------- the two runtime evaluators
class ExitLUT:
    """What the pixel shader binds. One object, two modes, and the mode is the
    entire experiment: `joint` fetches the chapter's two-channel table;
    `sep_2tau` and `sep_sq` fetch the scalar absorption table and multiply by a
    Fresnel constant at runtime.

    `mode` is not a quality setting. All three cost one fetch and one multiply;
    the separated modes are not faster, which is the chapter's point -- `the trap
    is free to avoid and there is no performance argument on the other side of
    it.`"""

    MODES = ('joint', 'sep_2tau', 'sep_sq')

    def __init__(self, mode='joint', n=N_TEXELS, tau_max=TAU_MAX):
        if mode not in self.MODES:
            raise ValueError('mode must be one of %r' % (self.MODES,))
        self.mode, self.n, self.tau_max = mode, n, tau_max
        if mode == 'joint':
            self.taus, self.tab = bake_joint(n, tau_max)
        else:
            self.taus, self.td, self.td2 = bake_factorised(n, tau_max)

    def __call__(self, tau):
        """tau: (...,3) per-band optical depth. Returns (T_esc, G_rt), each
        (...,3). One fetch per band in every mode."""
        tau = np.asarray(tau, float)
        if self.mode == 'joint':
            v = fetch(self.tab, tau, self.tau_max)      # (..., 3, 2, 3)
            # the fetch is per-band, so take band c's own row c
            idx = np.arange(3)
            return v[..., idx, 0, idx], v[..., idx, 1, idx]
        td = fetch(self.td, tau, self.tau_max)
        esc = td * OPT.T_OUT_DIFFUSE
        if self.mode == 'sep_2tau':
            rt = fetch(self.td2, tau, self.tau_max) * OPT.R_INT
        else:
            rt = td * td * OPT.R_INT
        return esc, rt

    def clamp_frac(self, tau):
        """The share of queries that saturated the table's domain. An absolute
        row in the suite, because a table that is silently clamped over half a
        frame is not being tested at all."""
        tau = np.asarray(tau, float)
        return float(np.mean(tau > self.tau_max))


# ------------------------------------------------- the measurement, in closed form
def factorisation_error(tau):
    """Every number the claim is made of, at one or many optical depths, with NO
    table and NO interpolation in the way: the joint integrals straight from
    `optics.py` against the two separated forms evaluated at the same tau.

    This is the term-level check the chapter demands -- `Check the term, not the
    chain` -- and it is deliberately separate from the pass, so that a frame-level
    agreement can never stand in for it.

    Returns a dict of (...,3) arrays. The four ratios are named for what they
    say, because this project has already confused two of them:

        esc_joint_over_sep  = T_joint/T_sep - 1   (>0: the separated form is DARK)
        esc_sep_under_joint = 1 - T_sep/T_joint   (the same fact, smaller number)
        rt_*_sep_over_joint = G_sep/G_joint - 1   (>0: the separated form is BRIGHT)
        rt_*_joint_under_sep= 1 - G_joint/G_sep   (the same fact, smaller number)
    """
    tau = np.atleast_1d(np.asarray(tau, float))
    flat = tau.reshape(-1)
    je = np.array([OPT.slab_esc(1.0, np.array([t, t, t])) for t in flat])
    jr = np.array([OPT.slab_trap(1.0, np.array([t, t, t])) for t in flat])
    td = OPT._e3(flat)[:, None]
    td2 = OPT._e3(2.0 * flat)[:, None]
    se = td * OPT.T_OUT_DIFFUSE[None]
    sr2 = td2 * OPT.R_INT[None]
    srq = td * td * OPT.R_INT[None]
    sh = tau.shape + (3,)
    out = {
        'tau': tau,
        'esc_joint': je.reshape(sh), 'esc_sep': se.reshape(sh),
        'rt_joint': jr.reshape(sh),
        'rt_sep_2tau': sr2.reshape(sh), 'rt_sep_sq': srq.reshape(sh),
        'esc_joint_over_sep': (je / se - 1.0).reshape(sh),
        'esc_sep_under_joint': (1.0 - se / je).reshape(sh),
        'rt_2tau_sep_over_joint': (sr2 / jr - 1.0).reshape(sh),
        'rt_2tau_joint_under_sep': (1.0 - jr / sr2).reshape(sh),
        'rt_sq_sep_over_joint': (srq / jr - 1.0).reshape(sh),
        'rt_sq_joint_under_sep': (1.0 - jr / srq).reshape(sh),
    }
    return out


def at_depth(dep, absorb=None):
    """`factorisation_error` at a PHYSICAL depth rather than at an optical one.

    The difference matters and it is easy to lose: at one depth the three bands
    sit at three DIFFERENT taus, so the answer is the diagonal of the (3 tau x 3
    band) block `factorisation_error` returns, not one of its rows. Reading a row
    instead mixes one band's optical depth with another band's Fresnel, and that
    off-diagonal read is worth 0.25 pp on the round trip at this pool's depth --
    small, but it is the difference between reproducing the chapter's table and
    nearly reproducing it."""
    a = OPT.ABS if absorb is None else np.asarray(absorb, float)
    blk = factorisation_error(a * float(dep))
    idx = np.arange(3)
    out = {'tau': a * float(dep), 'dep': float(dep)}
    for k, v in blk.items():
        if k == 'tau':
            continue
        out[k] = np.asarray(v)[idx, idx]
    return out


def composed_albedo(rho_bed, cos_sun, dep, mode, absorb=None):
    """`rho_water` composed through a chosen mode -- the CHAIN, so that the
    chapter's `an end-to-end agreement of a few percent is not evidence about a
    factor that is wrong by twenty` can be shown rather than repeated.

    Identical to `optics.rho_water` in every factor except which pair of
    (T_esc, G_rt) goes in. `mode='exact'` calls `optics.rho_water` itself, so
    the exact branch is the shipped function and not a re-derivation of it."""
    a = OPT.ABS if absorb is None else np.asarray(absorb, float)
    if mode == 'exact':
        return OPT.rho_water(rho_bed, cos_sun, dep, absorb=absorb)
    tau = a * dep
    td = OPT._e3(np.atleast_1d(tau))
    esc = td * OPT.T_OUT_DIFFUSE
    if mode == 'sep_2tau':
        rt = OPT._e3(np.atleast_1d(2.0 * tau)) * OPT.R_INT
    elif mode == 'sep_sq':
        rt = td * td * OPT.R_INT
    else:
        raise ValueError(mode)
    st = np.sqrt(np.maximum(1.0 - np.asarray(cos_sun, float) ** 2, 0.)) / OPT.IOR
    tsl = np.exp(-a * dep / np.sqrt(1.0 - st ** 2))
    rho_bed = np.asarray(rho_bed)
    return ((1.0 - OPT.fresnel(cos_sun)) * tsl * rho_bed * esc
            / (1.0 - rho_bed * rt))
