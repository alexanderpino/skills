"""First light on the bay -- the beach scene, rendered.

    python3 beach_render.py             # the three frames and the numbers
    python3 beach_render.py --fast      # half resolution, for a check run

WHAT THIS FILE IS AND IS NOT. Three waves built a bathymetry, a wave transform
in two dimensions and a suite, and there was still no image of water. This makes
one. It is not a beauty pass: it has no foam model, no spray, no plunging lip,
no swash, no vegetation and no village, and the two of those that are visible in
the reference frames are named in the figure captions rather than approximated
quietly.

WHAT IT IS FOR is bar section A, which is a FALSIFICATION and not a look:

    a backlit wave face reads green while the same water metres away reads
    grey-blue -- one liquid, two colours, one exposure -- so THE COLOUR IS THE
    PATH, and a renderer that tints its water body has been falsified.

Nothing in this file tints water. There is one set of inherent optical
properties for the water mass (`beach_optics.iops`) and one sediment field
computed from the wave's own bed dissipation; the green and the grey-blue are
two different TRANSPORTS through the same coefficients, and the frames print the
ratio between them in scene-linear before any tone curve.

THE STANDING RULING ON MEASUREMENT IS KEPT BY CONSTRUCTION. Every number this
file reports is taken from the float32/float64 radiance buffer. The PNG writer
is the last four lines of `_save` and nothing reads back through it.

THE SUN IS THE POOL'S, AND THAT IS A DECISION. `atmosphere.py` carries Aljezur
at 2026-08-10 18:41 WEST -- elevation 21.02 deg, azimuth 273.75 deg, air mass
2.77 -- and its SUN_COL, sky gradient and two derived illuminants all descend
from that one geometry. The bar's surf frames are 2026-08-12 18:08, elevation
27.17 deg, azimuth 268.31 deg: the same site, two days later, 33 minutes
earlier, 6.15 deg higher and 5.44 deg round. THREE REASONS THE POOL'S SUN IS THE
ONE USED HERE and none of them is convenience:

  1. It is DERIVED. `SUN_COL` is Rayleigh extinction at that air mass and the
     whole environment -- disc, aureole, deck illuminant, sub-surface illuminant
     -- is built from it with nothing left to choose. Moving the sun means
     re-deriving all four, which is a round of its own and would move the pool's
     frames if done in place.
  2. It is UN-ECLIPSED. The bar's surf frames are 12 August, roughly half an
     hour before the greatest phase of a solar eclipse whose extent at this
     longitude the bar records as `?`. The 10 August sun is a day clear of it.
  3. It is the SAME QUADRANT. Both are a low west sun over the Atlantic, which
     is the only geometric fact section A needs: the waves run east and the sun
     is behind them, so the faces are backlit. That is not arranged -- it is
     what a west-facing coast at 18:00 does.

`atmosphere.py`'s own comment says the site and shoot block is "the first of the
two blocks a second scene replaces". It has not been replaced, and the reason is
a FINDING about the module rather than a shortcut -- see README-beach.md, "What
the shared modules would not stretch to".
"""
import math
import sys
import time

import numpy as np
from PIL import Image

import beach as B
import beach_optics as BO
import beach_foam as FM
import optics as OPT
import atmosphere as ATM


FAST = '--fast' in sys.argv
OUT = '../../gauntlet/sea/evidence'


# ============================================================ scene placement
# WORLD AXES ARE `atmosphere.py`'S: +x east, +y north, +z up. `beach.py`'s x is
# CROSS-SHORE INCREASING SHOREWARD and its y is alongshore, and at Aljezur the
# coast faces WEST -- so shoreward is east and the two x axes are the same axis
# with the same sign. Nothing is rotated and nothing needs to be.
#
# THE CONSEQUENCE IS THE WHOLE OF SECTION A. The sun is at azimuth 273.7 deg,
# which is 3.7 deg north of due west, and the waves travel toward +x, which is
# east. So the sun is BEHIND every wave face in this scene, at 21 deg of
# elevation, and every face is backlit. That is not a lighting choice: it is
# what a west-facing Atlantic beach does at six in the evening, and it is why
# the reference photographs show what they show.
SUN = ATM.SUN_DIR                       # unit, TOWARD the sun
SUN_EL = ATM.SUN_EL
SUN_AZ = ATM.SUN_AZ
BAR_SURF_EL, BAR_SURF_AZ = 27.17, 268.31        # the bar's own surf frames

# --- albedos, and both are `?` ------------------------------------------------
# There is no reflectance measurement of this coast and the bar's standing ruling
# forbids reading one off a photograph. Both of these are DECLARED, both are
# marked, and the wet/dry pair is the one that is NOT declared twice: bar
# section H3 records that wet sand darkens by the trapped series this project
# already derived for the pool's liner, and that it "applies to sand unchanged".
# So `SAND_WET` is `optics.wet_albedo(SAND_DRY)` and carries no new number.
SAND_DRY = np.array([0.45, 0.39, 0.30])         # `?` quartz beach sand
ROCK_DRY = np.array([0.12, 0.11, 0.10])         # `?` schist/greywacke cliff
PLAIN_DRY = np.array([0.17, 0.19, 0.12])        # `?` the coastal plain's dry
                                                # summer scrub. Bar K2 puts dune
                                                # vegetation and the village out
                                                # of scope, so this is one flat
                                                # albedo standing where a plant
                                                # model would go, and the caption
                                                # says so.
PLAIN_Z = 6.0                                   # m, above which the land is
                                                # plain rather than beach --
                                                # `beach.BEACH_HEIGHT` is 2 m and
                                                # the swash reaches 0.5 m, so
                                                # this is three berms up.
SAND_WET = OPT.wet_albedo(SAND_DRY)[0]
ROCK_WET = OPT.wet_albedo(ROCK_DRY)[0]


# ==================================================== the scene's water column
class Water:
    """The optical state of every cell of the bay, computed once.

    THREE FIELDS AND ONE OF THEM IS NOT A CONSTANT. The water MASS carries
    a_ph(440) and a_CDOM(440) -- the same everywhere, because a water mass is
    the same water everywhere -- and the mineral load is a FIELD, computed from
    the wave's own bed dissipation by `beach_optics.suspended_load`. Bar section
    D asks for exactly this: `b` coupled to the wave field, not a property of
    the body.
    """

    def __init__(self, bay):
        tr = bay['tr']
        self.x, self.y = bay['x'], bay['y']
        self.h = bay['h']
        self.d = tr['d']
        self.H = tr['H']
        self.S = tr['S']
        self.k = tr['k']
        self.theta = tr['theta']
        self.brk = tr['brk']
        tr_u = dict(tr)
        tr_u['T'] = tr['T']
        self.u_orb = B.orbital_velocity(tr_u)
        self.w_s = B.settling_velocity()
        self.susp = BO.suspended_load(self.u_orb, self.d, self.w_s)

        self.io_clear = BO.iops()                       # the water mass alone
        # the suspension layer's own IOPs, per cell
        spm = np.clip(self.susp['spm'], 0.0, 5.0e4)
        self.io_layer_b = BO.iops(spm=spm)['b']
        self.io_layer_bb = BO.BB_OVER_B * self.io_layer_b
        self.io_layer_a = self.io_clear['a'][None, None] + 0.0 * self.io_layer_b

        self.d_bot = np.minimum(self.susp['delta'], self.d)
        self.d_top = np.maximum(self.d - self.d_bot, 0.0)
        col = BO.column_reflectance(
            self.io_clear['a'], self.io_clear['b_b'], self.d_top,
            self.io_layer_a, self.io_layer_bb, self.d_bot)
        self.R_col = col['R']
        self.c_bar = col['c_bar']

        # --- the bed under all of it. `optics.rho_water` is the pool's own
        # trapped series and it is IMPORTED with the coastal absorption passed
        # in through the `absorb` argument the extraction left open. It takes a
        # SCALAR depth, so it is evaluated on a depth ladder and interpolated --
        # and the interpolation error is a row in the suite rather than a claim
        # here. The absorption used for the ladder is the CLEAR water's: the
        # bed's own light is the one term the suspension layer hides rather than
        # colours, and the layer's opacity is already carried by `t_col`.
        # --- WAVE 5: the surface is no longer a sinusoid. `beach.surface_state`
        # returns the bound second harmonic's amplitude ratio r and its phase
        # psi from THIS transform and no other -- the mixed-field trap in the
        # place it would be most expensive, because a surface steep in the wrong
        # cells is a defect no still frame reports.
        ss = B.surface_state(tr)
        self.r2, self.psi2 = ss['r'], ss['psi']
        self.r2_raw, self.r2_lim = ss['r_raw'], ss['limit']
        self.r2_clamped = ss['clamped_fraction']
        self.Ur = ss['ursell']

        self.dep_lut = np.geomspace(0.05, 20.0, 48)
        self.rho_lut = np.stack([
            OPT.rho_water(SAND_WET, math.sin(math.radians(SUN_EL)), float(dd),
                          absorb=self.io_clear['a'] + self.io_clear['b_b'])
            for dd in self.dep_lut])
        self.t_col = col['t_col']

        # --- WAVE 6: THE WHITE, and it is three fields because bar section C
        # says it is three mechanisms. None of them is a texture and none of
        # them is on the crests.
        #
        #   q_b       Battjes & Janssen's breaking FRACTION -- the source of the
        #             surface deck. The transform's own `brk` is a boolean and a
        #             boolean cannot say how much of the surface goes white.
        #   alpha     the entrained-air void fraction, from the transform's own
        #             D_w through Lamarre & Melville's energy budget.
        #   plume     the participating medium that fraction implies, and the
        #             DIFFUSE TRANSMITTANCE is the number bar section C is
        #             actually about: it is what stops the bed being visible.
        self.T_wave = tr['T']
        self.omega = 2.0 * math.pi / tr['T']
        self.c_phase = tr['c']
        self.D_w = tr['D_w']
        self.q_b = FM.breaking_fraction_2d(self.d, self.H)
        self.bub = FM.bubble_scatter()
        self.air = FM.entrained_air(self.D_w, self.H, self.T_wave)
        # THE PLUME IS EVALUATED PER PIXEL, NOT PER CELL, because it is
        # PHASE-STRUCTURED: <tau>_vol is under a second against a nine-second
        # period, so the air one bore front entrains is gone before the next
        # arrives and the plume belongs to the front rather than to the surf
        # zone. `plume_phase_factor` redistributes the budget's void fraction
        # over the phase with a mean of exactly 1, so the energy budget is
        # untouched and only its placement changes. The cell-mean version is
        # kept for the printed diagnostics and for the suite.
        self.plume = FM.plume_optics(self.air['alpha'], self.air['r_32'],
                                     self.air['d_p'], self.bub['g'],
                                     self.bub['bb_over_b'], self.io_clear['a'])
        self.raft = FM.foam_raft(self.air['Q'], r_32=self.air['r_32'])
        # THE OPEN SEA IS THE OTHER HALF OF THIS WAVE. Beyond the domain there
        # is no bar and no breaking, so the only white out there is
        # WHITECAPPING, driven by the SAME U10 the glitter path's width reports.
        # One wind, two readouts, one frame -- and the answer is in `wind_check`.
        self.m_wind = float(FM.covering_measure_wind(BO.U10))
        self.W_wind = float(FM.whitecap_coverage(BO.U10))
        # the foam tail's e-folding length, for the caption and for the suite
        self.tau_foam = FM.foam_residence(salt=True)
        self.foam_tail = FM.foam_tail_length(self.c_phase, self.tau_foam)

    def sample(self, xw, yw, field):
        """Bilinear sample of a cell field at world (x, y), edges clamped."""
        fx = np.clip((xw - self.x[0]) / (self.x[1] - self.x[0]), 0,
                     self.x.size - 1.001)
        fy = np.clip((yw - self.y[0]) / (self.y[1] - self.y[0]), 0,
                     self.y.size - 1.001)
        i0, j0 = fx.astype(np.int32), fy.astype(np.int32)
        tx, ty = (fx - i0)[..., None], (fy - j0)[..., None]
        if field.ndim == 2:
            tx, ty = tx[..., 0], ty[..., 0]
        f = field
        return ((f[j0, i0] * (1 - tx) + f[j0, i0 + 1] * tx) * (1 - ty)
                + (f[j0 + 1, i0] * (1 - tx) + f[j0 + 1, i0 + 1] * tx) * ty)


# ================================================== the free surface, at one t
# THE WAVE FIELD IS THE TRANSFORM'S OWN. `transform_2d` accumulates the phase S
# along the march, so the free surface at a single instant is
#
#       eta(x, y) = (H/2) cos(S - omega t)
#
# with H the transform's shoaled, refracted, broken height. NOTHING IS ADDED:
# no noise, no octaves, no chop. What that costs is stated rather than hidden --
# the resolved field carries only the swell, so its mean square slope is
# 0.0013 against the 0.0335 that Cox & Munk put on a 6 m/s sea. The missing 96%
# is not omitted, it is carried STATISTICALLY, in the glitter's slope
# distribution and in nothing else; see `shade_water`.
# BEYOND THE DOMAIN THERE IS STILL A SEA, and the first writing of this file
# did not say so. `Water.sample` clamps its indices at the grid's edge, so every
# ray that landed seaward of x = 0 read the x = 0 column's phase -- one value of
# S for the whole open ocean, which draws the swell as INFINITE STRIPES running
# to the horizon. It looked like aliasing and it was a boundary condition.
#
# What is out there is the sea state the transform was GIVEN: H0, T and theta0
# in deep water, so eta = (H0/2) cos(k0 (x cos th0 + y sin th0)) with
# k0 = omega^2/g. Nothing new is declared -- the offshore boundary condition is
# already an input to this scene, and this is the same input drawn rather than
# assumed. The two fields are blended over the last 60 m of the domain so the
# seam does not draw a line at 1 km.
#
# WAVE 5 REPLACES THE SINUSOID, and the replacement carries no new constant.
# The surface is second-order Stokes,
#
#       eta = (H/2) [ cos(phi) + r cos(2 phi + psi) ],   phi = S - omega t
#
# with r = beach.stokes2_ratio(H, k, d) -- which is 2*Ur in shallow water, the
# file's OWN Ursell number -- and psi = -(pi/2) f_brk rotating the same harmonic
# from a peaked crest to a pitched-forward bore. r is clamped at the validity
# limit `beach.stokes2_crest_limit(psi)`, above which the shape grows a false
# crest inside its own trough; how much of this scene the clamp bites is
# reported by `surface_report` rather than hidden, and it is most of it.
_K0 = (2.0 * math.pi / B.T_SWELL) ** 2 / B.G
_TH0 = B.THETA0_SWELL
# The open ocean beyond the domain is the SAME theory at the same order, and
# there it is nearly nothing: deep water gives C -> 2 and r -> a k0/2, which at
# this swell is under two per cent. Written out rather than set to zero, so the
# offshore boundary is the same physics as the inshore one and the seam has
# nothing to hide.
_R0 = 0.5 * B.H0_SWELL * _K0 / 2.0


def free_surface(w, xw, yw, t=0.0):
    H = w.sample(xw, yw, w.H)
    S = w.sample(xw, yw, w.S)
    r = w.sample(xw, yw, w.r2)
    psi = w.sample(xw, yw, w.psi2)
    om = 2.0 * math.pi / B.T_SWELL
    # ONE EXPRESSION FOR THE SHAPE, and it lives in `beach.py`. Writing the
    # sum out here as well would put the surface in two places, which is the
    # duplication this project's own standing ruling on shared physics is
    # about -- one file down from where it usually bites.
    ph = S - om * t
    eta = B.nonlinear_eta(0.5 * H, r, psi, ph)
    ph0 = _K0 * (xw * math.cos(_TH0) + yw * math.sin(_TH0)) - om * t
    far = B.nonlinear_eta(0.5 * B.H0_SWELL, _R0, 0.0, ph0)
    f = np.clip((w.x[0] + 60.0 - xw) / 60.0, 0.0, 1.0)
    return eta * (1.0 - f) + far * f


def surface_slope(w, xw, yw, t=0.0, eps=0.5):
    """The RESOLVED slope of the free surface, by central difference.

    `eps` WAS ONE METRE AND WAVE 5 HALVED IT, for a reason that is arithmetic
    rather than taste. A central difference of step eps reports a sinusoid of
    wavenumber q at sin(q eps)/(q eps) of its true slope. Waves 1-4 carried only
    the primary, q = k <= 0.29 here, and lost 1.4% at eps = 1 m. The bound
    second harmonic is at 2k, and at eps = 1 m it loses 5.4% -- the difference
    operator would have quietly eaten a third of the steepening this wave is
    measuring. At eps = 0.5 m the primary loses 0.35% and the harmonic 1.4%,
    and both are inside every tolerance that reads this. The suite carries the
    gain factor as a row rather than this comment carrying it as a claim.
    """
    e = eps
    zx = (free_surface(w, xw + e, yw, t) - free_surface(w, xw - e, yw, t)) / (2 * e)
    zy = (free_surface(w, xw, yw + e, t) - free_surface(w, xw, yw - e, t)) / (2 * e)
    return zx, zy


# ======================================================================= camera
class Camera:
    def __init__(self, pos, look, fov_deg, w, h, up=(0, 0, 1)):
        self.pos = np.asarray(pos, float)
        f = np.asarray(look, float) - self.pos
        f /= np.linalg.norm(f)
        u = np.asarray(up, float)
        r = np.cross(f, u)
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        self.f, self.r, self.u = f, r, u
        self.w, self.h = w, h
        self.tan = math.tan(math.radians(fov_deg) / 2.0)

    def rays(self):
        px = (np.arange(self.w) + 0.5) / self.w * 2.0 - 1.0
        py = 1.0 - (np.arange(self.h) + 0.5) / self.h * 2.0
        gx, gy = np.meshgrid(px, py)
        asp = self.w / self.h
        d = (self.f[None, None] + gx[..., None] * self.tan * asp * self.r[None, None]
             + gy[..., None] * self.tan * self.u[None, None])
        return d / np.linalg.norm(d, axis=-1, keepdims=True)


# ================================================================ intersection
def trace(cam, w, t=0.0, n_march=384, far=40000.0):
    """Ray-cast the combined surface: land where h > 0, free surface where not.

    The water surface is found ANALYTICALLY and then refined, which is what
    makes a 20 km sea affordable: a ray with d_z < 0 meets the plane z = 0 at a
    known t, and |eta| <= 1 m, so three Newton steps against eta land on the
    real surface. The land is found by marching, but only over the segment
    BEFORE the plane hit -- nothing above sea level can be behind it.
    """
    D = cam.rays()
    O = cam.pos
    ny, nx = D.shape[:2]
    dz = D[..., 2]
    with np.errstate(divide='ignore', invalid='ignore'):
        t_pl = np.where(dz < -1e-9, -O[2] / dz, np.inf)
    t_pl = np.minimum(t_pl, far)

    # --- land: march from the camera to the plane hit
    hit_land = np.zeros((ny, nx), bool)
    t_land = np.full((ny, nx), np.inf)
    s = (np.arange(n_march) + 1.0) / n_march
    s = s ** 2                                  # dense near the camera
    prev_above = np.ones((ny, nx), bool)
    prev_t = np.zeros((ny, nx))
    for k in range(n_march):
        tt = np.minimum(t_pl, far) * s[k]
        p = O[None, None] + D * tt[..., None]
        hb = w.sample(p[..., 0], p[..., 1], w.h)
        above = p[..., 2] > hb
        new = prev_above & (~above) & (~hit_land) & np.isfinite(tt)
        if new.any():
            lo, hi = prev_t[new], tt[new]
            for _ in range(24):                 # bisect to a centimetre
                mid = 0.5 * (lo + hi)
                pm = O[None] + D[new] * mid[..., None]
                hm = w.sample(pm[..., 0], pm[..., 1], w.h)
                up = pm[..., 2] > hm
                lo = np.where(up, mid, lo)
                hi = np.where(up, hi, mid)
            t_land[new] = 0.5 * (lo + hi)
            hit_land[new] = True
        prev_above, prev_t = above, tt

    # --- water: Newton against the free surface, from the plane hit
    t_w = t_pl.copy()
    ok = np.isfinite(t_w)
    for _ in range(4):
        p = O[None, None] + D * t_w[..., None]
        e = np.where(ok, free_surface(w, p[..., 0], p[..., 1], t), 0.0)
        # z(t) = O_z + t d_z ; want z = eta  ->  dt = (eta - z)/d_z
        t_w = np.where(ok, t_w + (e - p[..., 2]) / np.where(dz < -1e-9, dz, -1.0),
                       t_w)
    water = ok & (~hit_land | (t_w < t_land))
    return dict(D=D, t_land=t_land, hit_land=hit_land, t_water=t_w,
                water=water, t_pl=t_pl)


# ================================================================== the shading
def sky_radiance(D):
    """The environment MINUS the sun's disc. The disc is added back only where
    it belongs -- on the water, through the slope distribution, by
    `beach_optics.glitter_radiance` -- so that a specular highlight is a
    statistic and never a lobe pasted on a mirror direction."""
    sh = D.shape[:-1]
    f = D.reshape(-1, 3)
    L = ATM.env_diffuse(f[:, 0], f[:, 1], f[:, 2])
    return L.reshape(sh + (3,))


_ENV_NZ = np.linspace(-0.2, 1.0, 13)
_ENV_AZ = np.linspace(0.0, 2 * np.pi, 13)[:-1]
_ENV_LUT = np.array([[ATM.env_irradiance(
    math.sqrt(max(1 - nz * nz, 0.0)) * math.cos(az),
    math.sqrt(max(1 - nz * nz, 0.0)) * math.sin(az), nz,
    nmu=64, nph=128) for az in _ENV_AZ] for nz in _ENV_NZ])


def env_irr(N):
    """`atmosphere.env_irradiance` on a (nz, azimuth) lattice, interpolated.

    The exact call integrates 131072 directions per NORMAL and there are half a
    million normals in a frame. The lattice is 13 x 12 and bilinear between; the
    suite carries the interpolation against the exact integral on random normals
    rather than this comment asserting it is fine."""
    nz = np.clip(N[..., 2], -0.2, 1.0)
    az = np.arctan2(N[..., 1], N[..., 0]) % (2 * np.pi)
    fz = (nz - _ENV_NZ[0]) / (_ENV_NZ[1] - _ENV_NZ[0])
    fa = az / (_ENV_AZ[1] - _ENV_AZ[0])
    i0 = np.clip(fz.astype(np.int32), 0, len(_ENV_NZ) - 2)
    j0 = fa.astype(np.int32) % len(_ENV_AZ)
    j1 = (j0 + 1) % len(_ENV_AZ)
    tz = (fz - i0)[..., None]
    ta = (fa - fa.astype(np.int32))[..., None]
    a = _ENV_LUT[i0, j0] * (1 - ta) + _ENV_LUT[i0, j1] * ta
    b = _ENV_LUT[i0 + 1, j0] * (1 - ta) + _ENV_LUT[i0 + 1, j1] * ta
    return a * (1 - tz) + b * tz


E_SUN = ATM.E_SUN                       # normal irradiance, pi * SUN_COL
COS_SUN = math.sin(math.radians(SUN_EL))
E_DOWN_AIR = E_SUN * COS_SUN + np.pi * ATM.SKY_DECK     # on the horizontal


def shade_water(w, P, D, t_now):
    """The water, in four terms and not one of them is a colour.

        1  the sky, reflected            Fresnel(theta_v) x env_diffuse(mirror)
        2  the sun, reflected            Cox & Munk glitter, from the SLOPE
                                         DISTRIBUTION and no spread parameter
        3  what comes back OUT of the    (E_u/pi) T(theta_v)/n^2, with E_u from
           column                        the two-layer volume reflectance and
                                         the bed's trapped series
        4  the PATH THROUGH the face     Beer-Lambert on a + b_b along the
                                         chord the view ray cuts through the
                                         wave, lit by the sun BEHIND it

    Term 4 is section A. It is zero when the chord is zero and zero when the sun
    is not behind the face, and those two are the falsification: the green is
    not in the water, it is in the length.
    """
    xw, yw = P[..., 0], P[..., 1]
    zx, zy = surface_slope(w, xw, yw, t_now)
    Nn = np.stack([-zx, -zy, np.ones_like(zx)], -1)
    Nn /= np.linalg.norm(Nn, axis=-1, keepdims=True)
    V = -D                                          # toward the eye
    cos_v = np.clip((Nn * V).sum(-1), 1e-4, 1.0)

    # ---- 1, the sky
    Rf = OPT.fresnel(cos_v)
    M = D - 2.0 * (D * Nn).sum(-1)[..., None] * Nn  # mirror direction
    M /= np.linalg.norm(M, axis=-1, keepdims=True)
    L_sky = sky_radiance(M) * Rf

    # ---- 2, the sun, as a statistic
    # THE RESOLVED SLOPE IS SUBTRACTED FROM THE VARIANCE AND NOT IGNORED. The
    # swell this file draws already carries mss_resolved; the glitter must carry
    # only what the grid does NOT resolve, or the surface is rough twice.
    su2, sc2 = BO.cox_munk_mss(BO.U10)
    L_glit = BO.glitter_radiance(SUN, D, u10=BO.U10)

    # ---- 3, out of the column
    R_col = w.sample(xw, yw, w.R_col)
    dep = np.maximum(w.sample(xw, yw, w.d), 0.02)
    c_bar = w.sample(xw, yw, w.c_bar)
    t_col = w.sample(xw, yw, w.t_col)
    rho_bed = np.stack([np.interp(dep, w.dep_lut, w.rho_lut[:, c])
                        for c in range(3)], -1)
    E_dn_w = (E_SUN * COS_SUN * (1.0 - OPT.fresnel(COS_SUN))[None]
              + np.pi * ATM.SKY_DECK * (1.0 - OPT.R_EXT)[None])
    R_bed = rho_bed * t_col
    R_sub = R_col + R_bed

    # ---- 3b, THE ENTRAINED AIR, AND IT IS A LAYER ON TOP OF ALL OF THAT.
    # Bar section C: "where the wave mouth goes white and opaque, and THE BED
    # STOPS BEING VISIBLE THROUGH IT. If a renderer whitens without hiding what
    # is behind, it has modelled the symptom."
    #
    # So the plume is not a lerp toward white. It is a slab of reflectance R_p
    # and diffuse transmittance T_p over a substrate of reflectance R_sub, and
    # the two are coupled by the standard adding series -- light goes down
    # through the plume, bounces off the column and the bed, comes back up
    # through the plume, and some of it is sent down again:
    #
    #       R_total = R_p + T_p^2 R_sub / (1 - R_p R_sub)
    #
    # The bed's share of what leaves the water is the SECOND term with R_sub
    # replaced by the bed's own R_bed, and `bed_visibility` below reports it
    # with the plume in and out. R_p and T_p come from `beach_foam.plume_optics`
    # and their sum is 1 minus what the water between the bubbles absorbs; a
    # plume that reflected without transmitting less would not conserve energy
    # and the suite has a row that says so.
    ph = w.sample(xw, yw, w.S) - w.omega * t_now
    age = FM.age_from_phase(ph, w.omega)
    if getattr(w, 'plume_on', True):
        alpha_p = (w.sample(xw, yw, w.air['alpha'])
                   * FM.plume_phase_factor(age, w.T_wave, w.air['tau_vol']))
        po = FM.plume_optics(np.minimum(alpha_p, 0.30), w.air['r_32'],
                             w.sample(xw, yw, w.air['d_p']), w.bub['g'],
                             w.bub['bb_over_b'], w.io_clear['a'])
        R_p, T_p = po['R'], po['T']
    else:
        # THE CONTROL PANEL, and it is one field zeroed. R_p = 0 and T_p = 1 is
        # exactly "no entrained air": the adding series collapses to R_sub and
        # every other term in this function is untouched, which is what makes
        # the pair a measurement rather than two pictures.
        R_p = np.zeros_like(R_sub)
        T_p = np.ones_like(R_sub)
    coup = 1.0 / np.maximum(1.0 - R_p * R_sub, 1e-9)
    bed_factor = T_p * T_p * coup          # 1 with no plume, by construction
    R_tot = R_p + bed_factor * R_sub
    R_bed_seen = bed_factor * R_bed
    E_up = E_dn_w * R_tot
    L_up = OPT.out_of_water(E_up / np.pi) * (1.0 - Rf)

    # ---- 4, THE PATH. The chord a view ray cuts through a wave face.
    #
    # The face is a WEDGE: the free surface stands eta above the still level and
    # the ray enters it obliquely, so the length of water between where the ray
    # crosses the surface and where it leaves the far side of the crest is
    #
    #       L_path = (eta - eta_far) / |cos of the ray against the face|
    #
    # -- and this file computes it the honest way, by marching the refracted ray
    # to where it exits, rather than by a thickness parameter. `chord` below is
    # that march. Where the sun is not behind the face the term is zeroed by its
    # own geometry: the source of term 4 is the SUN SEEN THROUGH the water, and
    # a face turned away from the sun has none.
    L_path, chord, lit = through_face(w, P, D, t_now, Nn, dep, c_bar)

    # ---- THE SURFACE DECK. Bar section C's first mechanism, and it is a
    # COVERAGE MASK -- not a particle system, not a texture, not a crest tint.
    #
    # WHERE IT IS. Not on the crest. Foam is laid down BY the breaking crest,
    # which then runs away from it at the celerity while the water it floats on
    # creeps forward at the Stokes drift; foam of age a therefore lies (c - u) a
    # behind the crest, and the mask is an exponential tail with an e-folding
    # length of c * tau_foam -- about 17 m on a 40 m wave here. The AGE is the
    # transform's own phase and nothing is advected: for a wave of permanent
    # form the phase IS the age, exactly.
    #
    # HOW MUCH OF IT. A Poisson covering measure, so the two sources add and the
    # coverage saturates at 1 by construction: Q_b/T from Battjes & Janssen in
    # the surf zone, and Monahan & O'Muircheartaigh's whitecapping from the wind
    # everywhere -- the SAME U10 the glitter path's width is a readout of.
    #
    # HOW BRIGHT. A pile of plates: the raft is n_walls bubble walls each
    # reflecting the bar's own 1 - 1/n^2, and the raft's THICKNESS is the air
    # arriving at the surface times the residence time, not a chosen depth.
    q_b = w.sample(xw, yw, w.q_b)
    cov1, m_cov = FM.surface_foam(q_b, w.T_wave, age, BO.U10, w.tau_foam)
    if not getattr(w, 'foam_on', True):
        cov1 = np.zeros_like(cov1)
    cov = cov1[..., None]
    R_raft = np.stack([w.sample(xw, yw, w.raft['R_pile'][..., c])
                       for c in range(3)], -1)
    # THE OPEN SEA'S RAFT IS NOT THIS SCENE'S. `R_pile` is built from the
    # surf-zone plume's own air flux, and beyond the domain there is no plume
    # here -- the wave field out there is the offshore boundary condition and
    # carries no breaking. A whitecap's raft is nonetheless a raft, so the floor
    # is the bar's OWN CONSTANT, which is what a SINGLE bubble wall reflects and
    # therefore the least a stack of them can. Marked rather than blended: the
    # open sea's foam brightness is a lower bound in this render, and at
    # W = 0.0017 coverage it moves the frame by nothing measurable.
    R_raft = np.maximum(R_raft, FM.FOAM_WHITE[None, None])
    L_foam = R_raft * (E_DOWN_AIR / np.pi)[None, None]

    L = L_sky + L_glit + L_up + L_path
    L = L * (1.0 - cov) + L_foam * cov
    return dict(L=L, L_sky=L_sky, L_glit=L_glit, L_up=L_up, L_path=L_path,
                chord=chord, cov=cov[..., 0], lit=lit, cos_v=cos_v,
                age=age, q_b=q_b, m_cov=m_cov, R_p=R_p, T_p=T_p,
                R_bed_seen=R_bed_seen, R_bed=R_bed, R_sub=R_sub, R_tot=R_tot,
                R_raft=R_raft, bed_factor=bed_factor, dep=dep, t_col=t_col,
                E_dn_w=E_dn_w)


def through_face(w, P, D, t_now, Nn, dep, c_bar, n_step=32, reach=24.0):
    """Section A's transport: what the sun leaves behind after crossing a wave.

    The ray refracts at the surface (`optics.refract`, the shared module's own
    Snell with its TIR branch), then this marches it forward until either the
    free surface comes back down to meet it -- which is the far side of the
    crest -- or it has crossed `reach` metres, at which point the face is not a
    face and there is nothing behind it. The chord is where it exits.

    WHAT LIGHTS IT is the sun's own beam, refracted in on the FAR side, so the
    term carries `max(0, -SUN . face normal on the far side)` -- which is what
    makes it vanish for a face turned away from the sun. There is no ambient
    term inside it, deliberately: bar section I2 records that a barrel's
    interior is lit THROUGH ITS OWN WALL and that lighting it with ambient sky
    misses the whole mechanism. The same is true of a wave face two orders
    smaller.
    """
    eta_r = 1.0 / OPT.IOR[1]                 # green's; the chord is geometric
    T = np.stack(OPT.refract(D[..., 0], D[..., 1], D[..., 2],
                             Nn[..., 0], Nn[..., 1], Nn[..., 2], eta_r), -1)
    Tn = np.linalg.norm(T, axis=-1, keepdims=True)
    T = T / np.where(Tn > 1e-9, Tn, 1.0)
    step = reach / n_step
    chord = np.zeros(P.shape[:-1])
    exited = np.zeros(P.shape[:-1], bool)
    Q = P.copy()
    g_prev = np.zeros(P.shape[:-1])                 # eta - z, positive in water
    for m in range(n_step):
        Qn = Q + T * step
        e = free_surface(w, Qn[..., 0], Qn[..., 1], t_now)
        g = e - Qn[..., 2]
        out = (g < 0.0) & (~exited)
        # LINEAR REFINE, and it is not cosmetic. The cuvette inversion below
        # reads c off d(ln T)/d(chord), so a chord quantised to the march step
        # puts a staircase into the very derivative being measured. One linear
        # interpolation on the crossing removes it.
        frac = np.where(out, g_prev / np.maximum(g_prev - g, 1e-9), 1.0)
        chord = np.where(exited, chord, chord + step * np.clip(frac, 0.0, 1.0))
        exited = exited | out
        Q, g_prev = Qn, g
    chord = np.where(exited, chord, 0.0)
    # the far side's own normal, where the beam gets in
    zx, zy = surface_slope(w, Q[..., 0], Q[..., 1], t_now)
    Nf = np.stack([-zx, -zy, np.ones_like(zx)], -1)
    Nf /= np.linalg.norm(Nf, axis=-1, keepdims=True)
    lit = np.clip((Nf * SUN[None, None]).sum(-1), 0.0, 1.0)
    L_in = (E_SUN[None, None] * lit[..., None]
            * (1.0 - OPT.fresnel(np.clip(lit, 1e-4, 1.0))) / np.pi)
    a = BO.iops()['a'][None, None] * np.ones_like(L_in)
    bb = BO.iops()['b_b'][None, None] * np.ones_like(L_in)
    L = L_in * np.exp(-(a + bb) * chord[..., None])
    return L * np.where(exited, 1.0, 0.0)[..., None], chord, lit


def shade_land(w, P, D):
    """Sand and rock, and the wet band that comes for free.

    Bar section H3: wet sand darkens because a thin film traps light between the
    surface and the substrate -- the trapped series this project already derived
    for the pool's liner as `wet_albedo` -- and it "applies to sand unchanged".
    So there is no wet-sand colour in this file. There is `optics.wet_albedo`
    of the dry one, and the boundary between them is the reach of the swash,
    which is `beach.runup_hunt` at this scene's own Iribarren number.
    """
    xw, yw = P[..., 0], P[..., 1]
    e = 1.5
    hz = w.sample(xw, yw, w.h)
    hx = (w.sample(xw + e, yw, w.h) - w.sample(xw - e, yw, w.h)) / (2 * e)
    hy = (w.sample(xw, yw + e, w.h) - w.sample(xw, yw - e, w.h)) / (2 * e)
    N = np.stack([-hx, -hy, np.ones_like(hx)], -1)
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    rock = np.clip((np.abs(hx) + np.abs(hy) - 0.35) / 0.5, 0.0, 1.0)[..., None]
    plain = np.clip((hz - PLAIN_Z) / 4.0, 0.0, 1.0)[..., None] * (1 - rock)
    wet = np.clip((RUNUP - hz) / 0.35, 0.0, 1.0)[..., None]
    sand = 1.0 - rock - plain
    alb = ((SAND_DRY[None, None] * (1 - wet) + SAND_WET[None, None] * wet)
           * sand
           + (ROCK_DRY[None, None] * (1 - wet) + ROCK_WET[None, None] * wet)
           * rock
           + PLAIN_DRY[None, None] * plain)
    ndl = np.clip((N * SUN[None, None]).sum(-1), 0.0, 1.0)
    L = alb * (E_SUN[None, None] * ndl[..., None] / np.pi + env_irr(N))
    return L


# the swash's own reach, from the wave field rather than from a paint line
_XI = None
RUNUP = 0.0


def _set_runup():
    global _XI, RUNUP
    sc = B.run_scene()
    tr = sc['tr']
    b = B.breaker_state(tr)
    i = b['i_cell']
    slope = abs(float(np.gradient(tr['h'], tr['dx'])[i]))
    L0 = B.deep_wavelength(B.T_SWELL)
    _XI = B.iribarren(slope, B.H0_SWELL, L0)
    RUNUP = B.runup_hunt(B.H0_SWELL, _XI)


# ==================================================================== tone map
# THE EXPOSURE IS DERIVED AND IT IS THE SAME FOR EVERY FRAME. A percentile of
# the frame's own histogram is an auto-exposure, and an auto-exposure is exactly
# what bar section A's "one exposure" forbids -- two frames of the same water
# would then be scaled differently and their ratio would mean nothing. So the
# white point is a PROPERTY OF THE ILLUMINANT: the radiance of a perfect white
# Lambertian card lying in this sun,
#
#       WHITE = (E_sun cos(theta_s) + E_sky) / pi
#
# which is 5.16 in the green here. A 0.45 sand reads 0.45 of it; the sea reads
# about a tenth; the glitter reads forty times it AND CLIPS, which is what a
# photograph of a glitter path does and is not a defect of the tone map.
WHITE = float(E_DOWN_AIR[1] / np.pi)


# WAVE 4'S CAPTIONS, KEPT AND NO LONGER WRITTEN. `s4-bay-render.png` and
# `s4-cuvette.png` are on disk with this text burned into them and they are not
# regenerated -- s4 is the LINEAR surface and the pair s4/s5 is the evidence, so
# overwriting it would destroy the comparison. They stay here so a reader can
# see which text belongs to which frame, and with one correction on the record:
# CAP_CUV's "0.1443 of slope, 8.21 deg" is wave 4's measurement of the LINEAR
# surface and is still true of s4; the nonlinear surface reads 15.78 deg, and
# neither reaches 41.48 -- see `_cap_bay5` and README-beach.md N7 for why no
# surface of a steady wave ever will.
CAP_BAY = (
    "s4  THE BAY FROM THE CLIFF EDGE -- for bar section J.  Bed and wave field from beach.py (wave 3's coastal loop and 2-D transform); optics from beach_optics.py; sun, sky and Fresnel imported from the pool's atmosphere.py / optics.py, unchanged.",
    "READ THIS BEFORE READING THE FRAME.  (1) THE FOAM IS A PLACEHOLDER: a saturating function of the breaking fraction put on the crests, with no advection, no decay, no entrained-air medium and no spray.  Bar section C names three mechanisms in three different representations; none is modelled, it is an OPEN row in the suite, and NOTHING about foam extent, texture or brightness may be read off this image.  (2) THE COASTAL PLAIN IS ONE DECLARED ALBEDO standing where a vegetation model would go; bar K2 puts dune vegetation and the village out of scope.  (3) THE FRAMING IS THE LANDFORM'S, NOT A COMPOSITION: bar J's photograph is from a headland with sea on three sides, and wave 3's loop gives 46 m of plan curvature over 1408 m of coast -- a nearly straight cliffed shore with a beach strip metres wide -- so there is no headland in this bed to stand on.  COMPARABLE TO J in its shore-parallel surf lines and its colour ladder (2G/(R+B) = 0.961 deep, 1.014 at 2-5 m, 1.130 over the shallows).  NOT COMPARABLE in its beach.",
)
CAP_GLIT = (
    's4  THE GLITTER PATH -- for bar section K.  Cox & Munk (1954) slope statistics at U10 = 6 m/s (mss = 0.03348), exact Fresnel from optics.py, sun irradiance from atmosphere.py, and the Jacobian dw_v = 4 cos(omega) cos^3(beta) dz derived beside itself.',
    "THERE IS NO SPREAD PARAMETER ANYWHERE IN THIS RENDER.  The path's width is a readout of the mean square slope: 14.96 deg in the near field, 6.63 deg at the horizon -- it NARROWS toward the horizon by 2.26x while brightening 14x, which is bar K1's own prediction from the geometry.  width/sqrt(mss) is constant to 1.7% over a factor of five in wind.  THE WIDTHS ARE MEASURED IN ANGLE, from the closed form, NOT off this image -- bar K3: do not read a level off the path.  The sea is flat-Earth here, so the image places the horizon 0.203 deg = sqrt(2h/R) too high.  The path CLIPS: the exposure is a derived white point (a white Lambertian card in this sun, 5.16 green) and the path is forty times it, which is what a photograph of a glitter path does.  The wind is `?`.",
)
CAP_CUV = (
    's4  THE VARIABLE-PATH CUVETTE -- for bar section A.  LEFT backlit (sun behind the water), RIGHT front-lit (sun behind the camera).  ONLY THE OBSERVER MOVES BETWEEN THE PANELS; the sun does not.  Thickness ramps 0 m at the top to 3 m at the bottom.',
    "THIS IS A STAND-IN AND THE WEDGE IS NOT A WAVE.  A ray entering water is confined to the Snell cone, so a sightline travelling ALONG a crest -- which is what a backlit wave face is -- needs a face steeper than 90 - asin(1/n) = 41.48 deg.  This scene's linear free surface reaches 0.1443 of slope, which is 8.21 deg: six times too gentle.  Section A's geometry cannot be rendered from a height field, and that puts it beside section F's plunging lip, one step earlier and for the same structural reason. EVERYTHING INSIDE THE WEDGE IS THE SCENE'S: the same IOPs, the same sun, optics.fresnel on both faces, optics.refract with its TIR branch, the same Beer-Lambert and the same HG lobe whose g = 0.9132 was DERIVED from chapter 28's b_f >= 50 b_b. The grade is 1.355 backlit and 1.348 front-lit -- the same, because the grade is the PATH and the path does not know where the sun is.  What differs is the forward glow: 5.07% of the backlit pixel, 0.00% of the front-lit one.  Transmittance 2G/(R+B) = 1.0000 at zero path.",
)


# --- wave 5's captions carry their own measurements, computed at write time --
# A CAPTION WITH A NUMBER TYPED INTO IT GOES STALE THE FIRST TIME THE RUN MOVES.
# Wave 4's captions carry literals and two of them are already wrong by this
# wave (8.21 deg, 0.1443). These are formatted from the run that drew the frame.
def _cap_bay5(s):
    return (
        's5  THE BAY FROM THE CLIFF EDGE, NONLINEAR SURFACE -- the pair to '
        's4-bay-render.png, which is the same camera, the same bed, the same '
        'optics and the SAME SUN with a sinusoidal surface. One field changed: '
        'the free surface is now second-order Stokes, eta = (H/2)[cos(phi) + '
        'r cos(2 phi + psi)].',
        'NOTHING IS AUTHORED AND NOTHING NEW IS DECLARED. r = (Hk/8) C(kd) is '
        'the bound second harmonic of the transform\'s own H, k and d, and in '
        'shallow water it is exactly 2x the Ursell number beach.py has computed '
        'since wave 1 and spent only on the sediment. psi = -(pi/2) f_brk '
        'rotates that same harmonic from a peaked crest to a pitched-forward '
        'bore, using the breaking fraction the transform already carries. '
        'THE STEEPEST FACE WENT FROM %.2f TO %.2f DEGREES (x%.2f). It does NOT '
        'reach the %.2f deg a lengthwise in-water sightline needs, and it '
        'cannot: Stokes\' 120 deg corner caps ANY wave of permanent form at a '
        '30 deg face, so bar section A is unreachable from a single-valued '
        'surface as a matter of proof and not of effort. '
        'VALIDITY IS REPORTED, NOT ASSUMED: the median Ursell number here is '
        '%.1f against the Stokes/cnoidal boundary at 0.5, and the '
        'secondary-crest clamp bites on %.0f%% of the wet bay -- this is a '
        'shallow-water scene and second-order Stokes is spent in it. '
        'THE FOAM IS STILL A PLACEHOLDER: a saturating function of the '
        'breaking fraction put on the crests, with no advection, no decay, no '
        'entrained-air medium and no spray; it is an OPEN row in the suite and '
        'nothing about foam extent, texture or brightness may be read off this '
        'image. The coastal plain is one declared albedo. The framing is the '
        'landform\'s: there is no headland in this bed to stand on.'
        % (math.degrees(math.atan(s['lin'])), math.degrees(math.atan(s['nl'])),
           s['nl'] / s['lin'], math.degrees(math.atan(s['need'])),
           s['ur_med'], 100.0 * s['clamped']),
    )


def _cap_face5(s, c, m):
    lin, nl = c['linear'], c['nonlinear']
    del m                       # the face/body pair needs a face; there is none
    return (
        's5  THE SURF ZONE CLOSE UP, LINEAR (LEFT) AND NONLINEAR (RIGHT) -- '
        'one camera, one bed, one sun, one instant of phase, and ONE FIELD '
        'CHANGED: the second harmonic r is zero on the left and (Hk/8)C(kd) on '
        'the right. Eye 8 m above the still level, 26 deg field, looking WEST '
        'into a 21 deg sun that is behind the waves because the coast faces '
        'west.',
        'WHAT CHANGED: crests sharper, troughs longer and flatter, the steepest '
        'face %.2f -> %.2f deg. WHAT DID NOT, AND IT IS BAR SECTION A. Section '
        'A asks for a face reading green against grey-blue water metres away '
        'in one exposure -- light that has come THROUGH the wave. Neither '
        'panel contains one such pixel: the fraction of water pixels whose '
        'view ray leaves the far side of a crest is %.4f on the left and %.4f '
        'on the right, and both are zero. THE SHORTFALL IS A THEOREM, NOT AN '
        'EFFORT. A ray entering water is confined to the Snell cone, so a '
        'lengthwise sightline needs a face steeper than 90 - asin(1/n) = %.2f '
        'deg, while Stokes\' 120 deg corner caps EVERY wave of permanent form '
        '-- Stokes at any order, cnoidal, solitary -- at a 30 deg face. No '
        'single-valued height field closes the 11 deg between them, so section '
        'A belongs beside bar section F\'s plunging lip by proof rather than '
        'by analogy. AND THE EYE HEIGHT IS PART OF IT: 8 m is what makes the '
        'crest shape legible at all, and the same 8 m tilts the view ray '
        'further into the water, so the frame that shows the steepening cannot '
        'be the frame that shows section A. THE FOAM IS A PLACEHOLDER -- a '
        'saturating function of the breaking fraction put on the crests, no '
        'advection, no decay, no entrained-air medium, no spray -- and it is '
        'the whitest thing in both panels, so read no white off either.'
        % (math.degrees(math.atan(s['lin'])), math.degrees(math.atan(s['nl'])),
           lin['frac'], nl['frac'], math.degrees(math.atan(s['need']))),
    )


# --- wave 6's captions, formatted from the run that drew the frame -----------
# WAVE 5 FOUND WAVE 4'S LITERALS HAD GONE STALE and said so in a comment. These
# take the measurement dicts and print them; there is no number typed into any
# string below.
def _cap_bay6(w, s, f):
    ct = f['clocks']
    brk = w.q_b > 0.5
    head = (
        's6  THE BAY FROM THE CLIFF EDGE, WITH THE WHITE -- the third frame at '
        'this camera. s4-bay-render.png is the linear surface, '
        's5-bay-render.png the nonlinear one with a FOAM PLACEHOLDER, and this '
        'is the same camera, the same bed, the same optics and the same sun '
        'with bar section C\'s THREE MECHANISMS in place of it.')
    body = (
        'THE PLACEHOLDER IS GONE AND NOTHING REPLACED IT WITH A TEXTURE. '
        'SURFACE FOAM is a coverage mask: a Poisson covering measure Q_b/T '
        'from Battjes & Janssen plus Monahan & O\'Muircheartaigh\'s '
        'whitecapping at the SAME U10 = %.1f m/s the glitter path\'s width '
        'reports, saturated through 1 - exp(-m). IT IS NOT ON THE CRESTS: foam '
        'of age a lies (c - u)a behind the crest that laid it, an exponential '
        'tail of e-folding length %.1f m on a %.0f m wave, and the age is the '
        'transform\'s own phase with nothing advected. Phase-averaged coverage '
        'runs %.3f where every wave breaks and %.5f on the open sea. '
        'ENTRAINED AIR is a participating medium and not a whitening: void '
        'fraction %.3g median in the breaking band, from the transform\'s own '
        'D_w through Lamarre & Melville (1991)\'s 30-50%% of the breaking '
        'dissipation, with a size-resolved steady state over the Deane & '
        'Stokes (2002) spectrum -- standing r_32 = %.2g m -- and a two-stream '
        'slab whose diffuse transmittance is what hides the bed. See '
        's6-entrained-air.png for that measurement. The plume is concentrated '
        'at the bore front, %.1fx its own time-mean, because its air clears in '
        '%.2f s against a %.0f s period. AIRBORNE SPRAY IS DEFERRED and this '
        'frame contains none: it is section C\'s smallest share of the white, '
        'it is a particle system and therefore a third representation, and bar '
        'section F already defers individual droplets beyond a statistical '
        'treatment. ALL THREE WHITEN FROM ONE IMPORTED CONSTANT, 1 - 1/n^2 = '
        '%.5f, which this file RECOVERS from a ray trace over a bubble\'s disc '
        'rather than restating -- and the trace adds a qualifier the bar does '
        'not carry: 43.9%% is a REFLECTANCE, not a backscatter fraction '
        '(b_b/b = %.4f), so the white is multiple scattering in a conservative '
        'medium and not one bright bounce. THREE CLOCKS, AND THE MIDDLE ONE IS '
        'NOT A NUMBER: %.2f s surface raft (Monahan & Zietlow 1969), %.2f s '
        'for the plume\'s AIR VOLUME, %.0f s for the suspension -- and the '
        'plume\'s own tau(r) = (d_p/2)/w(r) runs %.2f s to %.0f s across the '
        'bubble spectrum, so its air is gone in under a second while the area '
        'that scatters light is not. The coastal plain is still one declared '
        'albedo and the framing is still the landform\'s.'
        % (BO.U10,
           float(np.median(w.foam_tail[brk])) if brk.any() else 0.0,
           float(np.median(w.c_phase[brk] * w.T_wave)) if brk.any() else 0.0,
           f['cov_bar'][0], f['cov_bar'][3],
           float(np.median(w.air['alpha'][brk])) if brk.any() else 0.0,
           w.air['r_32'],
           float(FM.plume_phase_factor(0.0, w.T_wave, w.air['tau_vol'])),
           w.air['tau_vol'], w.T_wave,
           float(FM.TIR_FRAC), float(f['bub']['bb_over_b'][1]),
           ct['tau_foam'], ct['tau_air'], ct['tau_sed'],
           ct['tau_lo'], ct['tau_hi']))
    return (head, body)


def _cap_air6(w, f, bvis, bvis0):
    """LEFT no plume, RIGHT plume. Every number below is read out of the two
    measurement dicts the same run produced; none is typed in."""
    k = '1.5 - 3 m'
    if k not in bvis:
        k = sorted(bvis)[0]
    n, Rp, tcol, bfac, rbs, lbed, rb, share = bvis[k]
    n0, Rp0, tcol0, bfac0, rbs0, lbed0, rb0, share0 = bvis0[k]
    brk = w.q_b > 0.5
    b_med = float(np.median(w.plume['b'][brk])) if brk.any() else 0.0
    tau_med = float(np.median(w.plume['tau_prime'][..., 1][brk])) if brk.any() \
        else 0.0
    head = (
        's6  DOES THE BED STOP BEING VISIBLE THROUGH ENTRAINED AIR? LEFT the '
        'entrained-air medium REMOVED, RIGHT in place. ONE FIELD CHANGED -- the '
        'plume\'s reflectance and diffuse transmittance -- and every other term '
        'in the shader, the camera, the bed, the sun, the free surface and the '
        'surface foam identical. Eye 8 m up, wave 5\'s framing kept.')
    body = (
        'BAR SECTION C: "where the wave mouth goes white and opaque, and THE BED '
        'STOPS BEING VISIBLE THROUGH IT. If a renderer whitens without hiding '
        'what is behind, it has modelled the symptom." MEASURED IN ABSOLUTE '
        'SCENE-LINEAR UNITS, not as a ratio -- the first writing of this '
        'measurement WAS a ratio and it was blind, because in the breaking band '
        'the bed term underflows and a ratio of two near-zeros reported 1.6e-4 '
        'for a run with the plume switched off. Over %d pixels at %s depth the '
        'bed\'s radiance out of the water is %.3e with the plume and %.3e '
        'without, a factor of %.3g, and the plume\'s own transmittance factor '
        'T^2/(1 - R R_sub) is %.3e. THE PLUME IS NOT A LERP TOWARD WHITE: it is '
        'a slab of reflectance R = %.3f and diffuse transmittance over the '
        'column and the bed, coupled by the adding series, with a scattering '
        'coefficient b = %.4g m^-1 and a similarity-scaled optical depth of '
        '%.4g median in the breaking band -- 2 x 3 alpha/(4 r_32), the '
        'geometric-optics extinction of the bubble population, with alpha from '
        'the wave\'s own dissipation and NOT from a density slider. AND IT '
        'SEPARATES TWO THINGS THAT BOTH HIDE A BED: bar section D\'s suspended '
        'sediment leaves a column transmittance of %.3e here and bar section '
        'C\'s entrained air multiplies that again -- a render that credits one '
        'for the other has not distinguished them. The sphere formula for b is '
        'CLIPPED AT ITS OWN VALIDITY LIMIT alpha = 0.30, which bites on %.2f%% '
        'of the wet bay and is reported rather than applied silently. Airborne '
        'spray is DEFERRED and neither panel contains any.'
        % (n, k, lbed, lbed0, (lbed / lbed0) if lbed0 > 0 else float('nan'),
           bfac, Rp, b_med, tau_med, tcol, 100.0 * w.air['clipped_fraction']))
    return (head, body)


def _cap_wind6(w, ck):
    g = ck.get('glitter', {})
    gm, gc = g.get('measured'), g.get('closed')
    uw = ck.get('u_whitecap', (float('nan'),) * 3)
    ug = ck.get('u_glitter', float('nan'))
    sens = ck.get('sens', (float('nan'), float('nan')))
    nan = float('nan')
    head = (
        's6  ONE WIND, TWO READOUTS, ONE FRAME -- bar section K\'s glitter path '
        'and bar section C\'s open-water white, both driven by the SAME '
        'U10 = %.1f m/s and both measured back off the scene-linear buffer.'
        % BO.U10)
    body = (
        'THE GLITTER WIDTH IS A PERCENT-LEVEL INSTRUMENT AND THE WHITECAP '
        'COVERAGE IS NOT, AND THAT IS THE FINDING. Measured off this buffer and '
        'never off the PNG (bar K3): the path is %.3f deg wide at view elevation '
        '%.0f deg against %.3f deg from the closed form, %+.1f%%, and the '
        'difference is the RESOLVED swell, which the closed form does not carry '
        'and this surface does. Inverting through wave 4\'s width/sqrt(mss) '
        'invariant gives U10 = %.2f m/s. The whitecap coverage on the open sea, '
        'plan-area-weighted because a coverage is per unit HORIZONTAL area, is '
        '%.6f, and Monahan & O\'Muircheartaigh (1980) inverts it to U10 = %.2f '
        'm/s. THE TWO AGREE TO %.1f%%. But the EXPONENT ALONE -- 3.41 as '
        'universally quoted, 3.52 in the same paper\'s own optimal fit, an '
        'offset cubic in Callaghan et al. (2008) -- spreads the coverage\'s '
        'answer to %.2f-%.2f m/s, and the coefficient\'s spread is worse. THE '
        'NUMBERS: d(ln width)/dU = %.4f per m/s against d(ln W)/dU = %.4f per '
        'm/s, so a 1%% width measurement fixes the wind to %.3f m/s while a '
        'FACTOR OF THREE in coverage leaves %.2f m/s -- the width is %.0fx the '
        'instrument the coverage is. They agree here because one U10 drives '
        'both; what this frame establishes is that they could not have '
        'DISAGREED informatively. AND AT THIS WIND THE WHITECAPS ARE %.3f%% OF '
        'THE SEA SURFACE: a render with conspicuous open-water foam has a '
        'different wind from the one its glitter path reports. The sea is '
        'flat-Earth here and the path clips, as in s4 and s5.'
        % (gm['width'] if gm else nan, gm['el'] if gm else nan,
           gc['dphi'] if gc else nan,
           100 * (gm['width'] / gc['dphi'] - 1.0) if (gm and gc) else nan,
           ug, ck.get('W', nan), uw[0],
           100 * abs(ug / uw[0] - 1.0) if uw[0] else nan,
           uw[1], uw[2], sens[0], sens[1],
           0.01 / sens[0] if sens[0] else nan,
           math.log(3.0) / sens[1] if sens[1] else nan,
           (math.log(3.0) / sens[1]) / (0.01 / sens[0])
           if (sens[0] and sens[1]) else nan,
           100.0 * ck.get('W', nan)))
    return (head, body)


def clocks_figure(w, f, path):
    """Section E, drawn: three mechanisms, and the middle one is a SPECTRUM.

    The bar says the two clouds "overlap in space and are separated by their
    DECAY, not their appearance", and this is that sentence as a figure -- plus
    the thing the bar does not say, which is that the entrained air does not
    have A decay. THE X AXIS IS LOGARITHMIC because the quantities being
    compared span four decades, and a linear axis would show two of the three
    curves as vertical lines at the origin. Nothing is read back out of this
    image."""
    import beach_plot as P
    from PIL import ImageDraw
    ct = f['clocks']
    sp = w.air['pop']['spectrum']
    img = P.canvas(1000, 600)
    ax = P.Axes(img, (92, 56, 580, 320), (-0.7, 3.4), (0.0, 1.02),
                title='Section E: three mechanisms, and one of them is a spectrum',
                xlabel='log10 seconds since the break',
                ylabel='fraction remaining')
    ax.frame(xticks=[-0.5, 0.0, 1.0, 2.0, 3.0],
             yticks=[0, 0.25, 0.5, 0.75, 1.0])
    lt = np.linspace(-0.7, 3.4, 800)
    tt = 10.0 ** lt
    # the plume's SPREAD: the fastest and slowest sizes in the population
    ax.fill_between(lt, np.exp(-tt / sp['tau_at_rmax']),
                    np.exp(-tt / sp['tau_at_rmin']), (206, 224, 240))
    cols = ((196, 60, 60), (40, 110, 190), (150, 110, 40))
    for (tau, col) in ((ct['tau_foam'], cols[0]), (ct['tau_air'], cols[1]),
                       (ct['tau_sed'], cols[2])):
        ax.line(lt, np.exp(-tt / tau), col, 2)
        ax.vline(math.log10(tau), col, 1, (4, 4))
    P.legend(ax, [(cols[0], 'surface raft %.2f s  Monahan & Zietlow 1969 (P)'
                   % ct['tau_foam']),
                  (cols[1], 'entrained AIR %.2f s  <tau>_vol (derived)'
                   % ct['tau_air']),
                  (cols[2], 'suspension %.0f s  d/w_s, Soulsby (derived)'
                   % ct['tau_sed']),
                  ((176, 206, 232),
                   'the plume\'s own spread, %.2f-%.0f s over the sizes'
                   % (sp['tau_at_rmax'], sp['tau_at_rmin']))],
                 0.45, 0.97)
    ax2 = P.Axes(img, (672, 56, 950, 320), (2.0, 20.0),
                 (math.log10(1e-5), math.log10(2e-1)),
                 title='Whitecap coverage', xlabel='U10, m/s',
                 ylabel='log10 fraction')
    ax2.frame(xticks=[3, 6, 10, 14, 18],
              yticks=[math.log10(v) for v in (1e-5, 1e-4, 1e-3, 1e-2, 1e-1)],
              yfmt='%.0f')
    uu = np.linspace(2.0, 20.0, 300)
    ax2.line(uu, np.log10(np.maximum(FM.whitecap_coverage(uu), 1e-9)),
             (40, 110, 190), 2)
    ax2.line(uu, np.log10(np.maximum(
        FM.whitecap_coverage(uu, FM.MOM80_OPT_A, FM.MOM80_OPT_N), 1e-9)),
        (196, 60, 60), 2, (6, 5))
    ax2.vline(BO.U10, (28, 30, 34), 1, (3, 4))
    ax2.marker(BO.U10, math.log10(max(w.W_wind, 1e-9)), (28, 30, 34))
    # --- the caption, WRAPPED to the canvas by measuring rather than guessing
    txt = (
        'SECTION E ASKED FOR TWO TIMESCALES AND THE FILE PRODUCES THREE, AND '
        'THE MIDDLE ONE IS NOT A NUMBER. Every curve is from this scene\'s own '
        'fields. The surface raft is Monahan & Zietlow (1969), salt water, '
        'PUBLISHED, and the salt/fresh pair in that paper is a factor of 1.5 '
        'that makes the decay a bubble-stability property rather than a '
        'hydrodynamic one. The plume is a size-resolved steady state over the '
        'Deane & Stokes (2002) spectrum: each radius leaves at its own rise '
        'speed, tau(r) = (d_p/2)/w(r) with w from Schiller & Naumann\'s drag, '
        'so the shaded band IS the plume and the blue line is only its '
        'volume-weighted mean. The AIR is gone in %.2f s -- which is bar '
        'section E\'s "rises and bursts in seconds", recovered rather than '
        'assumed -- while the projected area that scatters light is dominated '
        'by the smallest bubbles present and lasts three orders of magnitude '
        'longer. THAT IS WHY A BREAK LEAVES A CLOUD: four seconds on, the deck '
        'has gone and what remains is a submerged haze. The suspension is '
        'd/w_s with Soulsby\'s law, a THIRD published relation, so no two of '
        'the three clocks share a source; at this bay\'s median depth of '
        '%.2f m the bed\'s own D50 of %.0f um clears in %.0f s, which is the '
        'bar\'s "minutes" met without adjustment -- but at 2 m it is %.0f s '
        'and minutes there would need %.0f um, the fine tail this file does '
        'not carry. RIGHT: Monahan & O\'Muircheartaigh (1980), the quoted fit '
        '(solid) and the same paper\'s own optimal fit (dashed). The dot is '
        'this render\'s wind, U10 = %.1f m/s, W = %.5f -- under a fifth of one '
        'per cent. `?` on the wind.'
        % (ct['tau_air'], ct['depth'], 1e6 * B.D50, ct['tau_sed'],
           2.0 / ct['w_s'], 1e6 * FM.d50_for_settling_time(120.0, 2.0),
           BO.U10, w.W_wind))
    d0 = ImageDraw.Draw(img)
    lines, cur = [], ''
    for word in txt.split(' '):
        trial = (cur + ' ' + word).strip() if cur else word
        if d0.textlength(trial, font=P.FONT_S) > img.width - 72 and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    P.caption(img, lines, x=36, y=376)
    P.save(img, path)
    return path


def _caption(img, lines, pad=12):
    """Burn the figure's own caption into the figure.

    Wave 1 stated its stamped rip channels this way and wave 3 stated their
    absence the same way, and the convention is worth more than any of the three
    models it qualifies: A PNG TRAVELS AND A README DOES NOT TRAVEL WITH IT. A
    frame that shows a placeholder and does not say so is the only kind of
    dishonesty a rendering project can commit silently.

    The text is WRAPPED TO THE IMAGE'S OWN WIDTH by measuring it, not by
    counting characters -- the first writing of this function hard-wrapped at a
    guessed column and cut every line off at the frame's right edge."""
    from PIL import ImageDraw
    from beach_plot import FONT_S, INK, MUTED
    w, h = img.size
    d0 = ImageDraw.Draw(img)
    wrapped = []
    for i, para in enumerate(lines):
        cur = ''
        for word in para.split(' '):
            trial = (cur + ' ' + word).strip() if cur else word
            if d0.textlength(trial, font=FONT_S) > w - 2 * pad and cur:
                wrapped.append((i, cur))
                cur = word
            else:
                cur = trial
        if cur:
            wrapped.append((i, cur))
    lh = 15
    band = pad * 2 + lh * len(wrapped)
    out = Image.new('RGB', (w, h + band), (250, 249, 246))
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    for k, (i, ln) in enumerate(wrapped):
        d.text((pad, h + pad + k * lh), ln, font=FONT_S,
               fill=INK if i == 0 else MUTED)
    return out


def _save(L, path, key=None, gamma=2.2, caption=None):
    """DISPLAY ONLY, and nothing in this file reads back through it.

    A single exposure `key` and a gamma. No filmic curve, no local adaptation,
    no white balance: the standing ruling is that a ratio between two levels
    does not survive a display-referred tone curve, and every ratio this file
    reports is taken from `L` before this function is called. The one thing the
    curve is allowed to do is make the frame legible."""
    k = WHITE if key is None else key
    img = np.clip(L / max(k, 1e-9), 0.0, 1.0) ** (1.0 / gamma)
    im = Image.fromarray((img * 255.0 + 0.5).astype(np.uint8))
    if caption is not None:
        im = _caption(im, caption)
    im.save(path)
    return k


# ============================================================== the whole frame
def downsample(L, ss):
    """Box-average a supersampled buffer, IN SCENE-LINEAR.

    2 x 2 samples per output pixel. It is here because the sea at a kilometre
    puts a whole 90 m wavelength inside one pixel, and a point sample of a
    surface whose slope swings through the specular direction inside the pixel
    reports either a glint or nothing -- which is the moire the first run of
    this file drew across the open water. Averaging RADIANCE is the only
    correct place to do it: averaging after the tone curve would average a
    display-referred quantity, which is the same mistake as measuring one."""
    if ss == 1:
        return L
    h, wd = L.shape[0] // ss, L.shape[1] // ss
    return L[:h * ss, :wd * ss].reshape(h, ss, wd, ss, 3).mean((1, 3))


def render(cam, w, t=0.0, label=''):
    tr = trace(cam, w, t)
    D, P = tr['D'], None
    L = np.zeros(D.shape[:2] + (3,))
    ex = {}

    # sky
    sky = sky_radiance(D) + BO.glitter_radiance(SUN, D, u10=BO.U10) * 0.0
    up = D[..., 2] >= 0.0
    L[up] = sky[up]

    # water
    mw = tr['water'] & ~up
    if mw.any():
        Pw = cam.pos[None] + tr['t_water'][mw][..., None] * D[mw]
        sh = shade_water(w, Pw[None], D[mw][None], t)
        L[mw] = sh['L'][0]
        ex['water'] = sh
        ex['water_mask'] = mw
        ex['water_P'] = Pw
    # land
    ml = tr['hit_land'] & ~tr['water'] & ~up
    if ml.any():
        Pl = cam.pos[None] + tr['t_land'][ml][..., None] * D[ml]
        L[ml] = shade_land(w, Pl[None], D[ml][None])[0]
        ex['land_mask'] = ml
    ex['trace'] = tr
    return L, ex


# ================================================================ measurements
def green_excess(L):
    """2G / (R + B), scene-linear. One number per pixel, 1.0 on any neutral.

    THIS IS THE INSTRUMENT FOR SECTION A and it is chosen so that the camera
    failures the bar lists cannot touch it: it is a WITHIN-FRAME ratio between
    channels of the SAME pixel, so an exposure, a white balance or a tone curve
    that acts on all three channels equally leaves it unchanged. It is measured
    here on the radiance buffer regardless -- the ruling is not to read a PNG --
    but it is the ratio that would survive if anyone did."""
    L = np.asarray(L, float)
    return 2.0 * L[..., 1] / np.maximum(L[..., 0] + L[..., 2], 1e-12)


def report_colour(ex, name):
    sh, mask = ex['water'], ex['water_mask']
    ch = sh['chord'][0]
    Lp = sh['L_path'][0]
    Lw = sh['L'][0]
    face = ch > 0.8
    body = ch <= 0.0
    out = {}
    print('  -- %s : the colour is the path' % name)
    if face.sum() > 50 and body.sum() > 50:
        gf = float(np.median(green_excess(Lw[face])))
        gb = float(np.median(green_excess(Lw[body])))
        out['face'], out['body'], out['ratio'] = gf, gb, gf / gb
        print('     green excess 2G/(R+B)   backlit face %.4f   body %.4f'
              '   ratio %.4f' % (gf, gb, gf / gb))
        print('     face pixels %d, body pixels %d, median chord %.2f m'
              % (face.sum(), body.sum(), float(np.median(ch[face]))))
    # the GRADE across the wedge, which is what section A asks for by name
    bins = [(0.0, 0.01), (0.5, 1.5), (1.5, 3.0), (3.0, 6.0), (6.0, 12.0),
            (12.0, 30.0)]
    print('     the grade across the wedge (chord bin -> green excess of the '
          'PATH term alone):')
    grade = []
    for lo, hi in bins:
        m = (ch >= lo) & (ch < hi) & (Lp[..., 1] > 0)
        if m.sum() < 20:
            continue
        g = float(np.median(green_excess(Lp[m])))
        grade.append((0.5 * (lo + hi), g, int(m.sum())))
        print('        %5.1f - %5.1f m   %8.4f   (%d px)' % (lo, hi, g, m.sum()))
    out['grade'] = grade
    return out


def cuvette(ex, name, io=None):
    """THE CUVETTE, run on the render's own scene-linear buffer.

    Two thicknesses in ONE frame, and the ratio removes the source. In the
    render the source is not identical between two pixels -- they see different
    parts of the sun's own beam through different far-side normals -- so the
    radiance is divided by that far-side geometry first, which is the only thing
    the ratio cannot cancel by itself. Everything else (the exposure, the
    interface transmittances, E_SUN) does cancel.
    """
    sh, io = ex['water'], (BO.iops() if io is None else io)
    ch = sh['chord'][0]
    lit = sh['lit'][0]
    Lp = sh['L_path'][0]
    m = (ch > 0.3) & (lit > 0.05) & (Lp[..., 1] > 1e-9)
    if m.sum() < 200:
        print('  -- %s : cuvette has too few path pixels (%d)' % (name, m.sum()))
        return None
    T = Lp[m] / (lit[m][..., None] * (1.0 - OPT.fresnel(
        np.clip(lit[m], 1e-4, 1.0))))
    Lm = ch[m]
    q = np.percentile(Lm, [20, 80])
    b1 = (Lm >= q[0] * 0.9) & (Lm <= q[0] * 1.1)
    b2 = (Lm >= q[1] * 0.9) & (Lm <= q[1] * 1.1)
    if b1.sum() < 20 or b2.sum() < 20:
        b1, b2 = Lm < np.median(Lm), Lm >= np.median(Lm)
    L1, L2 = float(np.mean(Lm[b1])), float(np.mean(Lm[b2]))
    T1, T2 = np.mean(T[b1], 0), np.mean(T[b2], 0)
    c_hat = BO.cuvette_c(T1, T2, L1, L2)
    c_true = io['a'] + io['b_b']
    print('  -- %s : the variable-path cuvette' % name)
    print('     L1 = %.2f m (n=%d), L2 = %.2f m (n=%d)'
          % (L1, b1.sum(), L2, b2.sum()))
    print('     c = -ln(T2/T1)/(L2-L1)   inverted %s' % np.round(c_hat, 5))
    print('                             put in   %s' % np.round(c_true, 5))
    print('                             error    %s %%'
          % np.round(100 * (c_hat / c_true - 1.0), 3))
    return dict(c_hat=c_hat, c_true=c_true, L1=L1, L2=L2)


# ======================================== WAVE 6 · THE WHITE, MEASURED
def foam_report(w):
    """The three mechanisms and their three clocks, printed from the scene.

    Everything here is a field of `Water`, computed in its constructor from the
    transform, and nothing in it is read off an image."""
    print('THE WHITE -- bar section C, three mechanisms')
    oc = FM.check_one_constant()
    print('  ONE CONSTANT: 1 - 1/n^2 = %.6f (green), per channel %s'
          % (oc['tir_frac'], np.round(oc['foam_white'], 5)))
    b = w.bub
    print('  the bubble, ray-traced (NOT written from that constant):')
    print('     TIR share of the disc %s  -- and it MATCHES'
          % np.round(b['tir_fraction'], 6))
    print('     reflected in total    %s  (TIR + partial Fresnel below it)'
          % np.round(b['reflected'], 6))
    print('     asymmetry g %s   backscatter b_b/b %s'
          % (np.round(b['g'], 4), np.round(b['bb_over_b'], 5)))
    print('     energy sum  %s' % np.round(b['total'], 9))
    a = w.air
    wet = w.d > B.D_MIN * 1.5
    brk = w.q_b > 0.5

    sp = a['pop']['spectrum']
    print('  the entrained air, from D_w and Lamarre & Melville:')
    print('     standing r_32 %.4g m; the SOURCE spectrum runs %.3g - %.3g m '
          'and each size leaves on its own clock, tau(r) = (d_p/2)/w(r), '
          'spanning %.2f s to %.0f s'
          % (a['r_32'], FM.R_MIN, a['r_max'], sp['tau_at_rmax'],
             sp['tau_at_rmin']))
    print('     <tau>_vol = %.3f s, so the AIR clears in under a second while '
          'the projected area that scatters does not -- the plume has no single '
          'decay time' % a['tau_vol'])
    print('     entrainment rate Q: median %.4g m/s in the breaking band'
          % (np.median(a['Q'][brk]) if brk.any() else float('nan')))
    print('     alpha: median %.4g in the breaking band, %.4g over the wet bay; '
          'clipped at 0.30 on %.2f%%'
          % (np.median(a['alpha'][brk]) if brk.any() else float('nan'),
             np.median(a['alpha'][wet]), 100 * a['clipped_fraction']))
    print('     b = %.4g m^-1 median in the breaking band'
          % (np.median(w.plume['b'][brk]) if brk.any() else float('nan')))
    print('     raft thickness %.4g m median in the breaking band (DERIVED: '
          'Q tau_foam / alpha_raft)'
          % (np.median(w.raft['h_raft'][brk]) if brk.any() else float('nan')))
    ct = FM.decay_times(np.median(w.H[wet]), np.median(w.d[wet]), w.T_wave)
    print('  THE THREE CLOCKS (bar section E asked for two):')
    print('     tau_foam %6.2f s  surface raft   PUBLISHED  Monahan & Zietlow '
          '1969 (salt)' % ct['tau_foam'])
    print('     tau_air  %6.2f s  the plume\'s AIR  DERIVED  <tau>_vol over the '
          'Deane & Stokes spectrum; the spectrum spans %.2f - %.0f s'
          % (ct['tau_air'], ct['tau_lo'], ct['tau_hi']))
    print('     tau_sed  %6.2f s  the suspension DERIVED    d/w_s, Soulsby'
          % ct['tau_sed'])
    print('     ordering air/foam = %.2f, sed/air = %.1f -- the bar\'s ordering '
          'holds for the AIR VOLUME and fails for the optical residue, which '
          'outlives the surface raft by orders of magnitude'
          % (ct['tau_air'] / ct['tau_foam'], ct['tau_sed'] / ct['tau_air']))
    print('     the bar says the sediment lasts MINUTES; at d = %.2f m that '
          'needs D50 = %.0f um against this file\'s bed D50 of %.0f um'
          % (ct['depth'], 1e6 * FM.d50_for_settling_time(120.0, ct['depth']),
             1e6 * B.D50))
    print('  the deck FLOATS: tail length c*tau = %.1f m median in the '
          'breaking band, against a local wavelength of %.1f m'
          % (np.median(w.foam_tail[brk]) if brk.any() else float('nan'),
             np.median(w.c_phase[brk] * w.T_wave) if brk.any() else float('nan')))
    # the coverage, phase-averaged, so the number is the SURFACE's and not a
    # pixel's -- a coverage read at one phase is a slice of a sawtooth
    aa = np.linspace(0.0, w.T_wave, 256)
    cov_bar = np.array([
        np.mean(FM.coverage(FM.covering_measure_break(qq, w.T_wave, aa,
                                                      w.tau_foam)
                            + w.m_wind))
        for qq in (1.0, 0.5, 0.1, 0.0)])
    print('  phase-averaged coverage at Q_b = 1.0 / 0.5 / 0.1 / 0.0 : %s'
          % np.round(cov_bar, 5))
    return dict(clocks=ct, cov_bar=cov_bar, bub=b)


def bed_visibility(w, ex, name):
    """DOES THE BED STOP BEING VISIBLE THROUGH THE ENTRAINED AIR? Measured, and
    in ABSOLUTE terms because the ratio alone is blind.

    THE FIRST WRITING OF THIS FUNCTION REPORTED ONLY R_bed_seen/R_bed AND IT WAS
    BLIND, in exactly the way this project has now been caught three times. In
    the breaking band the bed term underflows -- the SUSPENSION has already
    hidden it -- so the ratio divided one number near zero by another and
    reported 1.6e-4 for a run with the plume switched OFF, where the answer is 1
    by construction. Every row here is therefore an absolute quantity and the
    ratio is only ever `bed_factor`, which is computed forward from T and R and
    never by dividing two measurements.

    AND IT SEPARATES THE TWO THINGS THAT HIDE A BED. Bar section D's suspended
    sediment and bar section C's entrained air both do it, and a render that
    credits one for the other has not distinguished them:

        t_col       the suspension's own transmittance      (section D)
        bed_factor  the plume's, T^2/(1 - R R_sub)          (section C)

    Both are printed, per depth band, with the bed's own reflectance beside
    them so a band where there was never any bed light cannot masquerade as a
    band where the plume removed it.
    """
    sh = ex['water']
    q = sh['q_b'][0]
    dep = sh['dep'][0]
    bf = sh['bed_factor'][0][..., 1]
    tcol = sh['t_col'][0][..., 1]
    tau_p = sh['R_p'][0][..., 1]
    rb = sh['R_bed'][0][..., 1]
    rbs = sh['R_bed_seen'][0][..., 1]
    rt = np.maximum(sh['R_tot'][0][..., 1], 1e-30)
    # THE ABSOLUTE ROW. What the bed actually puts into the frame, in the same
    # scene-linear units as everything else this file prints.
    E = float(sh['E_dn_w'][0][..., 1]) if np.ndim(sh['E_dn_w']) else float(
        sh['E_dn_w'][1])
    L_bed = OPT.out_of_water(np.stack([rbs] * 3, -1) * E / np.pi)[..., 1]
    out = {}
    print('  -- %s : does the bed stop being visible?' % name)
    print('     %-16s %7s %10s %10s %10s %10s %10s'
          % ('depth band', 'n px', 'R_plume', 't_col(D)', 'bed_fac(C)',
             'R_bed_seen', 'L_bed'))
    for lab, sel in (('d < 1.5 m', dep < 1.5),
                     ('1.5 - 3 m', (dep >= 1.5) & (dep < 3.0)),
                     ('3 - 6 m', (dep >= 3.0) & (dep < 6.0)),
                     ('d > 6 m', dep >= 6.0),
                     ('Q_b > 0.9', q > 0.9)):
        if sel.sum() < 20:
            continue
        row = (int(sel.sum()), float(np.median(tau_p[sel])),
               float(np.median(tcol[sel])), float(np.median(bf[sel])),
               float(np.median(rbs[sel])), float(np.median(L_bed[sel])),
               float(np.median(rb[sel])), float(np.median(rbs[sel] / rt[sel])))
        out[lab] = row
        print('     %-16s %7d %10.4f %10.3e %10.3e %10.3e %10.3e'
              % (lab, row[0], row[1], row[2], row[3], row[4], row[5]))
    print('     R_plume is the plume\'s own reflectance (green); t_col is the '
          'SUSPENSION\'s')
    print('     transmittance and bed_fac the PLUME\'s, so section D and '
          'section C are')
    print('     separated; L_bed is absolute scene-linear radiance out of the '
          'water.')
    return out


def glitter_width_measured(L, cam, el_lo, el_hi, mask=None, n_bin=181,
                           span=45.0):
    """The path's width MEASURED OFF THE SCENE-LINEAR BUFFER, in angle.

    Not off the PNG -- bar K3 and the project's standing ruling both forbid it,
    and this reads `L` before `_save` is ever called. The profile is binned by
    the view azimuth's offset from the anti-solar bearing at a fixed band of
    view elevation, which is the same coordinate `beach_optics.
    glitter_azimuth_profile` uses, so the closed form and the render are being
    asked the same question.

    WHY THE TWO WILL NOT AGREE EXACTLY, and it is a result rather than an error:
    the closed form carries ONLY the unresolved slope statistics, while the
    render's surface is also tilted by the resolved swell. The render's path is
    therefore broader, by the swell's own mean square slope added in quadrature,
    and the difference is a measurement of how much slope the grid resolves.
    """
    D = cam.rays()
    r = -D
    ev = np.degrees(np.arcsin(np.clip(r[..., 2], -1.0, 1.0)))
    az = np.degrees(np.arctan2(r[..., 0], r[..., 1])) % 360.0
    dphi = (az - (SUN_AZ + 180.0) + 180.0) % 360.0 - 180.0
    sel = (ev >= el_lo) & (ev <= el_hi) & (np.abs(dphi) <= span)
    if mask is not None:
        sel = sel & mask
    if sel.sum() < 200:
        return None
    edges = np.linspace(-span, span, n_bin + 1)
    idx = np.clip(np.digitize(dphi[sel], edges) - 1, 0, n_bin - 1)
    g = L[..., 1][sel]
    prof = np.zeros(n_bin)
    cnt = np.zeros(n_bin)
    np.add.at(prof, idx, g)
    np.add.at(cnt, idx, 1.0)
    ok = cnt > 4
    if ok.sum() < 20:
        return None
    xc = 0.5 * (edges[:-1] + edges[1:])
    wdt, pk = BO.fwhm(xc[ok], prof[ok] / cnt[ok])
    return dict(width=wdt, peak=pk, n=int(sel.sum()),
                el=0.5 * (el_lo + el_hi))


def wind_check(w, L, cam, ex, el_band=(6.0, 14.0)):
    """ONE WIND, TWO READOUTS, ONE FRAME -- and whether they agree.

    Bar section K makes the glitter path's width a readout of the mean square
    slope and therefore of the wind. Section C's open-water white is
    WHITECAPPING, whose coverage is a published function of the same wind. This
    render drives both from one `beach_optics.U10`, so the question is not
    whether the inputs match -- it is whether the two OUTPUTS, measured back off
    the frame, return the same wind.

    THE COVERAGE IS AREA-WEIGHTED IN THE PLAN, because a coverage fraction is
    defined per unit HORIZONTAL area and a pixel near the horizon sees hundreds
    of times more of it than a pixel in the near field. The weight is the
    horizontal area a pixel's solid angle subtends, r^2/|D_z|, and reporting the
    unweighted mean instead would be a measurement of the camera.
    """
    sh, mw = ex['water'], ex['water_mask']
    tr = ex['trace']
    out = {}
    # --- the glitter, off the buffer
    gm = glitter_width_measured(L, cam, el_band[0], el_band[1], mask=mw)
    gc = BO.glitter_width_deg(SUN_EL, 0.5 * (el_band[0] + el_band[1]),
                              u10=BO.U10)
    out['glitter'] = dict(measured=gm, closed=gc)
    # --- the whitecaps, off the same buffer's coverage field
    q = sh['q_b'][0]
    cov = sh['cov'][0]
    rng = tr['t_water'][mw]
    dz = np.abs(tr['D'][..., 2][mw])
    wgt = rng ** 2 / np.maximum(dz, 1e-6)
    open_sea = (q < 1e-3) & (rng > 200.0)
    print('  -- ONE WIND, TWO READOUTS (bar C x bar K)')
    print('     put in:  U10 = %.2f m/s (beach_optics.U10, `?`)' % BO.U10)
    if gm is not None:
        mss_c = sum(BO.cox_munk_mss(BO.U10))
        # width/sqrt(mss) is the invariant wave 4 established; invert through it
        kk = gc['dphi'] / math.sqrt(mss_c)
        mss_m = (gm['width'] / kk) ** 2
        u_g = float(BO.wind_from_mss(mss_m))
        out['u_glitter'] = u_g
        print('     glitter: width %.3f deg measured over view elev %.0f-%.0f, '
              '%.3f deg from the closed form (%+.1f%%)'
              % (gm['width'], el_band[0], el_band[1], gc['dphi'],
                 100 * (gm['width'] / gc['dphi'] - 1.0)))
        print('              -> mss %.5f -> U10 = %.2f m/s' % (mss_m, u_g))
    if open_sea.sum() > 500:
        W = float((cov[open_sea] * wgt[open_sea]).sum() / wgt[open_sea].sum())
        W_raw = float(np.mean(cov[open_sea]))
        u_w, u_lo, u_hi = FM.wind_from_whitecap(W)
        out['W'] = W
        out['u_whitecap'] = (float(u_w), float(u_lo), float(u_hi))
        print('     whitecap: coverage %.6f plan-weighted (%.6f unweighted, '
              '%d px), law says %.6f' % (W, W_raw, open_sea.sum(), w.W_wind))
        print('              -> U10 = %.2f m/s, and the EXPONENT ALONE puts it '
              'in %.2f - %.2f' % (u_w, u_lo, u_hi))
        if 'u_glitter' in out:
            print('     THE TWO READOUTS: glitter %.2f m/s, whitecaps %.2f m/s, '
                  'apart by %.1f%%'
                  % (out['u_glitter'], u_w,
                     100 * abs(out['u_glitter'] / u_w - 1.0)))
            # the SENSITIVITIES, which are the real finding
            su2, sc2 = BO.cox_munk_mss(BO.U10)
            dmss_du = BO.CM_A_U + BO.CM_A_C
            dwid_du = 0.5 * dmss_du / (su2 + sc2)       # d(ln width)/dU
            dW_du = FM.MOM80_N / BO.U10                 # d(ln W)/dU
            out['sens'] = (dwid_du, dW_du)
            print('     SENSITIVITY at this wind: d(ln width)/dU = %.4f per '
                  'm/s, d(ln W)/dU = %.4f per m/s' % (dwid_du, dW_du))
            print('              a 1%% width measurement gives dU = %.3f m/s; '
                  'a FACTOR OF 3 in coverage gives dU = %.2f m/s'
                  % (0.01 / dwid_du, math.log(3.0) / dW_du))
    else:
        print('     whitecap: too few open-sea pixels (%d) in this frame'
              % open_sea.sum())
    return out


def glitter_table(sun_el=None, u10=None):
    sun_el = SUN_EL if sun_el is None else sun_el
    u10 = BO.U10 if u10 is None else u10
    su2, sc2 = BO.cox_munk_mss(u10)
    print('  -- the glitter path, Cox & Munk (1954)')
    print('     U10 = %.1f m/s  ->  sigma_u^2 = %.5f, sigma_c^2 = %.5f, '
          'mss = %.5f' % (u10, su2, sc2, su2 + sc2))
    print('     %-14s %10s %10s %10s' % ('view elev', 'd(phi) deg',
                                         'width deg', 'peak L (green)'))
    rows = []
    for ev in (25.0, sun_el, 15.0, 10.0, 6.0, 3.0, 1.5, 0.5, 0.2):
        r = BO.glitter_width_deg(sun_el, ev, u10=u10)
        rows.append((ev, r['dphi'], r['psi'], r['peak_L']))
        print('     %12.2f %10.3f %10.3f %10.4g'
              % (ev, r['dphi'], r['psi'], r['peak_L']))
    return rows


# ==================================================================== the runs
def main():
    t0 = time.time()
    _set_runup()
    print('sun: elevation %.2f deg, azimuth %.2f deg, air mass %.3f  '
          '(atmosphere.py, 2026-08-10 18:41 WEST)'
          % (SUN_EL, SUN_AZ, ATM.SUN_AM))
    print('the bar\'s surf frames are %.2f / %.2f -- %.2f deg higher, '
          '%.2f deg round' % (BAR_SURF_EL, BAR_SURF_AZ,
                              BAR_SURF_EL - SUN_EL, SUN_AZ - BAR_SURF_AZ))
    print('run-up: Iribarren xi = %.3f, R = %.2f m (beach.runup_hunt)'
          % (_XI, RUNUP))

    bay = B.run_bay()
    w = Water(bay)
    io = w.io_clear
    print()
    print('THE WATER MASS, three constituents, chapter 28:')
    print('  a_ph(440)   = %.4f m^-1   RECOVERED from the Jerlov 1C entry'
          % BO.A_PH_440)
    print('  a_CDOM(440) = %.4f m^-1   declared `?`' % BO.A_CDOM_440)
    print('  a  (R,G,B)  = %s m^-1' % np.round(io['a'], 5))
    print('  b  (R,G,B)  = %s m^-1  (pure water only, offshore)'
          % np.round(io['b'], 5))
    print('  b_b/b       = %.5f  ->  HG asymmetry g = %.4f  (derived)'
          % (BO.BB_OVER_B, BO.PHASE_G))
    print('  K_d         = %s m^-1,  Secchi %.2f m'
          % (np.round(BO.k_d(io['a'], io['b_b']), 4),
             BO.secchi(io['a'], io['b_b'])))
    print('  f (deep R = f b_b/(a+b_b)) = %.4f derived; literature ~0.33'
          % BO.F_GORDON)
    print()
    print('THE SEDIMENT, from the wave field and not from a slider:')
    ws = w.w_s
    print('  settling velocity w_s = %.4f m/s (beach.settling_velocity, '
          'D50 = %.2f mm)' % (ws, B.D50 * 1e3))
    for nm, mask in (('breaking zone', w.brk),
                     ('depth 2-4 m', (w.d > 2) & (w.d < 4)),
                     ('offshore, d > 6 m', w.d > 6)):
        print('  %-18s D_f %6.2f W/m2   M %6.3f kg/m2   layer %5.2f m   '
              'SPM_layer %7.1f mg/L   SPM_mean %6.1f mg/L'
              % (nm, np.median(w.susp['D_f'][mask]),
                 np.median(w.susp['M'][mask]),
                 np.median(w.susp['delta'][mask]),
                 np.median(w.susp['spm'][mask]),
                 np.median(w.susp['spm_bar'][mask])))
    print()

    srep = surface_report(w)
    print()
    frep = foam_report(w)
    print()

    sc = 0.5 if FAST else 1.0
    SS = 1 if FAST else 2
    W, H = int(900 * sc) * SS, int(508 * sc) * SS
    frames = {}

    # ---- THE TWO CAMERAS STAND ON THE CLIFF EDGE, and that is geometry
    # rather than composition: this coast's cliff is 20 m and the water starts
    # 26 m in front of it, so an eye at the edge sees the sea from the horizon
    # down to 39 deg of depression. Twenty metres further inland the plateau's
    # own brow cuts the near water off completely -- the first framing of this
    # file put the camera 270 m back and rendered a field of sand with a strip
    # of sea in it. Where a camera can stand is part of the landform.
    xj, cliff_j = cliff_edge(w, -640.0)
    # THE FRAMING IS CONSTRAINED BY THE LANDFORM AND THAT IS A FINDING, NOT A
    # COMPOSITION PROBLEM. Bar section J's photograph is taken from a HEADLAND,
    # with sea on three sides. Wave 3's coastal loop produced 46 m of plan
    # curvature over 1408 m of coast -- a nearly straight cliffed shore -- so
    # there is no headland in this bed to stand on, and an eye 1.7 m above a
    # flat coastal plain sees that plain fill every landward direction to the
    # horizon. The camera therefore looks WEST-NORTH-WEST, out over the water
    # with the coast receding on the right; that is the most J-like frame this
    # bed can give, and the gap between it and J is recorded in the README.
    az_j = math.radians(335.0)
    camJ = Camera((xj, -640.0, cliff_j + 1.7),
                  (xj + 800.0 * math.sin(az_j),
                   -640.0 + 800.0 * math.cos(az_j), cliff_j + 1.7 - 84.0),
                  48.0, W, H)
    LJ, exJ = render(camJ, w)
    frames['J'] = (LJ, exJ, camJ)

    # ---- K: the open sea and the glitter path, straight down the sun's
    # azimuth. The path runs from the horizon into the near field and its width
    # is measured in ANGLE, above, rather than in pixels here.
    az = math.radians(SUN_AZ)
    xk, cliff_k = cliff_edge(w, 0.0)
    camK = Camera((xk, 0.0, cliff_k + 1.7),
                  (xk + 300.0 * math.sin(az), 300.0 * math.cos(az),
                   cliff_k + 1.7 - 64.0), 34.0, W, H)
    LK, exK = render(camK, w)
    frames['K'] = (LK, exK, camK)

    # ---- F: THE BACKLIT FACE, wave 5's frame and the one section A is about.
    # The eye stands in the swash, 1.1 m above the still level, and looks WEST
    # into the sun with the surf zone between. Three things about this framing
    # are geometry rather than composition:
    #
    #   * the sun is behind the waves BY THE COAST'S ORIENTATION -- azimuth
    #     273.7 deg on a west-facing beach -- so this is the only direction the
    #     frame could face and still be section A's frame;
    #   * the eye is LOW, at 1.1 m, and that is not for drama. The refracted
    #     view ray inside the water dives at (90 - alpha) - asin(cos(alpha+
    #     delta)/n) below the horizontal, and delta -- the eye's own tilt -- is
    #     in that expression. An eye ABOVE the crest looking down adds to the
    #     dive; an eye at or below crest level subtracts from it. Section A's
    #     photographs are all taken from the beach with the face at eye level;
    #   * the camera sits shoreward of where H is largest, found from the wave
    #     field rather than placed, so the wave in frame is the one the
    #     transform says is about to break.
    #
    # AND THE SUN IS KEPT OUT OF FRAME, which is a measurement decision rather
    # than a compositional one. The first framing of this looked straight down
    # the sun's own azimuth and the glitter path -- forty times the white point
    # by the exposure this file derives -- clipped the entire frame to white.
    # A clipped frame cannot carry a colour ratio, and a colour ratio is the
    # only thing section A asks for. The view is therefore ~48 deg off the
    # sun's azimuth, which leaves the sun still BEHIND the waves (they run
    # east, any westward view is backlit) and out of the field.
    #
    # THE EYE IS AT 8 m AND THAT IS ITSELF PART OF THE FINDING. An eye in the
    # swash cannot SEE the shape of a wave face: at 1.5 m the crests are edge
    # on, one metre of relief at forty metres is 1.4 deg, and the frame is a
    # set of white bands. Eight metres of elevation resolves the crest and the
    # trough behind it -- and the same eight metres makes section A's sightline
    # WORSE, because the view ray's own downward tilt delta enters the dive
    # angle (90 - alpha) - asin(cos(alpha + delta)/n) with the same sign as the
    # face's shortfall. The frame that shows the steepening cannot be the frame
    # that shows section A, and that is not a framing problem.
    ib = int(np.argmax(np.max(w.H, axis=0)))
    jb = int(np.argmax(w.H[:, ib]))
    x_f = float(w.x[ib]) + 55.0
    y_f = float(w.y[jb]) + 55.0
    camF = Camera((x_f, y_f, 8.0), (x_f - 75.0, y_f - 75.0, 0.0), 26.0, W, H)
    LF, exF = render(camF, w)
    frames['F'] = (LF, exF, camF)
    # THE PAIR, and it is one field apart. The same camera, the same bed, the
    # same optics, the same sun, the same instant of phase; only r is zeroed.
    r_keep = w.r2
    w.r2 = np.zeros_like(w.r2)
    LF0, exF0 = render(camF, w)
    w.r2 = r_keep
    print('THE BACKLIT FACE FRAME: eye at x = %.0f m, y = %.0f m, z = %.1f m, '
          '%.0f deg off the sun\'s azimuth'
          % (x_f, y_f, camF.pos[2],
             abs(math.degrees(math.atan2(camF.f[0], camF.f[1])) % 360.0
                 - SUN_AZ)))
    print('  the wave it looks at: H = %.2f m in d = %.2f m, H/d = %.3f, '
          'Ur = %.2f, r = %.3f, f_brk = %.2f'
          % (w.H[jb, ib], w.d[jb, ib], w.H[jb, ib] / max(w.d[jb, ib], 1e-6),
             w.Ur[jb, ib], w.r2[jb, ib], -2.0 / np.pi * w.psi2[jb, ib]))
    mF = report_colour(exF, 'F, the backlit face, in the bay itself')
    print()
    crep = chord_report(w, camF)
    print()

    # ---- A: the cuvette, backlit and front-lit, and the face-slope finding
    face_slope_report(w)
    cvA = render_cuvette(back=True)
    cvB = render_cuvette(back=False)
    print('  cuvette: forward scattering angle %.1f deg backlit, %.1f deg '
          'front-lit' % (math.degrees(math.acos(np.clip(cvA['cos_sc'], -1, 1))),
                         math.degrees(math.acos(np.clip(cvB['cos_sc'], -1, 1)))))
    print('  the SAME HG lobe at those two angles: %.4g vs %.4g sr^-1'
          % (BO.hg_phase(BO.PHASE_G, cvA['cos_sc']),
             BO.hg_phase(BO.PHASE_G, cvB['cos_sc'])))

    print('MEASUREMENTS, all from the scene-linear buffer:')
    mA = cuvette_report(cvA, cvB)
    print()
    grows = glitter_table()
    print()
    horizon_check(LK, camK)
    print()
    bay_ladder(LJ, exJ, w)
    print()

    # ---- WAVE 6: the three whites, measured
    bvis = bed_visibility(w, exF, 'F, the surf zone close up')
    print()
    wchk = wind_check(w, LK, camK, exK)
    print()
    # THE CONTROL FRAME. One field zeroed -- the plume's R and T -- and nothing
    # else in the shader touched, so the pair is a measurement of what the
    # entrained air does and not two pictures of two scenes.
    w.plume_on = False
    LF_noair, exF_noair = render(camF, w)
    w.plume_on = True
    bvis0 = bed_visibility(w, exF_noair, 'F, with the entrained air REMOVED')
    print()

    # ---- write the frames
    # THE s4 AND s5 FRAMES ARE NOT OVERWRITTEN, and that is now a two-wave rule.
    # s4 is the LINEAR surface, s5 is the nonlinear one with the foam
    # PLACEHOLDER, and s6 is the same camera again with section C's three
    # mechanisms. Three frames, one camera, one bed, one sun, one field changed
    # each time -- overwriting either of the earlier two would destroy the only
    # thing that makes them evidence.
    kJ = _save(downsample(LJ, SS), '%s/s6-bay-render.png' % OUT,
               caption=_cap_bay6(w, srep, frep))
    gapF = np.zeros((LF.shape[0], 8 * SS, 3))
    kF = _save(downsample(np.concatenate([LF_noair, gapF, LF], axis=1), SS),
               '%s/s6-entrained-air.png' % OUT,
               caption=_cap_air6(w, frep, bvis, bvis0))
    kK = _save(downsample(LK, SS), '%s/s6-glitter-whitecap.png' % OUT,
               caption=_cap_wind6(w, wchk))
    clocks_figure(w, frep, '%s/s6-clocks.png' % OUT)
    print('exposure keys (99th pct of scene-linear): J %.4g  F %.4g  K %.4g'
          % (kJ, kF, kK))
    print('%.1f s' % (time.time() - t0))
    return dict(A=mA, glitter=grows, w=w, frames=frames, cvA=cvA, cvB=cvB,
                surface=srep, chord=crep, faceF=mF, foam=frep, bed=bvis,
                bed0=bvis0, wind=wchk)


# ======================================== the face slope, and why A needs more
def face_slope_report(w, n=40000):
    """WHAT THE LINEAR FREE SURFACE CAN AND CANNOT DO, measured before anything
    is claimed about section A.

    A view ray that enters water is compressed into the Snell cone: it can be no
    further than asin(1/n) = 48.6 deg from the surface's own normal. So a ray
    that is to travel ALONG a wave -- across the crest and out the far side,
    which is what a backlit face is -- needs the face's normal to be tilted at
    least (90 - 48.6) = 41.4 deg from the vertical. The face must be steeper
    than 41.4 degrees or no observer can see through it lengthwise, whatever
    the water is made of.

    This scene's free surface is eta = (H/2) cos(S): a linear wave, and its
    maximum slope is (H/2) k, which this function measures over the whole bay.
    """
    zx, zy = surface_slope(w, *np.meshgrid(
        np.linspace(w.x[0] + 5, w.x[-1] - 5, 900),
        np.linspace(w.y[0] + 20, w.y[-1] - 20, 300)))
    s = np.hypot(zx, zy)
    need = math.tan(math.pi / 2 - math.asin(1.0 / OPT.IOR[1]))
    print('THE FACE SLOPE, and it is a finding rather than a setting:')
    print('  max |grad eta| over the bay        %.4f  (%.2f deg)'
          % (s.max(), math.degrees(math.atan(s.max()))))
    print('  99.9th percentile                  %.4f  (%.2f deg)'
          % (np.percentile(s, 99.9),
             math.degrees(math.atan(np.percentile(s, 99.9)))))
    print('  needed for a lengthwise sightline  %.4f  (%.2f deg) = 90 - '
          'asin(1/n)' % (need, math.degrees(math.atan(need))))
    print('  -> short by %.2fx.' % (need / max(s.max(), 1e-9)))
    return float(s.max()), float(need)


# ============================== wave 5: what the nonlinear surface is and costs
def surface_report(w):
    """THE SURFACE'S OWN STATE, before any picture is drawn from it.

    Three things have to be on the record before the steepening can be claimed:
    how far past second-order Stokes this scene is (the Ursell number against
    the regime boundary), how much of it the validity clamp bites, and what the
    steepening actually bought on the face slope -- against 41.48 deg, and
    against the 30 deg that Stokes' corner caps EVERY wave of permanent form at.
    """
    wet = w.d > B.D_MIN
    Ur, r, rr, lim = w.Ur[wet], w.r2[wet], w.r2_raw[wet], w.r2_lim[wet]
    print('THE NONLINEAR SURFACE (wave 5), and its validity first:')
    print('  Ursell number over the wet bay   median %8.3f  p99 %8.3f  '
          'max %8.3f' % (np.median(Ur), np.percentile(Ur, 99), Ur.max()))
    print('  the Stokes/cnoidal boundary      Ur = %.3f   (U = 32 pi^2/3 in '
          'this file\'s normalisation)' % B.URSELL_STOKES_LIMIT)
    print('  fraction of the wet bay past it  %.3f' %
          np.mean(Ur > B.URSELL_STOKES_LIMIT))
    print('  r = b/a asked for by Stokes-2    median %8.3f  max %8.3f'
          % (np.median(rr), rr.max()))
    print('  the secondary-crest limit        %.3f .. %.3f  (1/4 bound, 1/2 '
          'pitched)' % (lim.min(), lim.max()))
    print('  fraction of the bay CLAMPED      %.3f   <- this scene is a '
          'shallow-water scene and' % w.r2_clamped)
    print('                                           second-order Stokes is '
          'spent before it starts')
    print('  r actually used                  median %8.4f  max %8.4f'
          % (np.median(r), r.max()))

    # --- the face slope, measured on the surface the renderer actually uses
    gx, gy = np.meshgrid(np.linspace(w.x[0] + 5, w.x[-1] - 5, 900),
                         np.linspace(w.y[0] + 20, w.y[-1] - 20, 300))
    zx, zy = surface_slope(w, gx, gy)
    s = np.hypot(zx, zy)
    # and the LINEAR surface on the same grid, for the pair -- one field, one
    # sampler, one difference operator; only r is zeroed.
    r_keep = w.r2
    w.r2 = np.zeros_like(w.r2)
    zx0, zy0 = surface_slope(w, gx, gy)
    w.r2 = r_keep
    s0 = np.hypot(zx0, zy0)
    need = math.tan(math.radians(B.snell_cone_face_deg()))
    corner = math.tan(math.radians(B.STOKES_FACE_DEG))

    def deg(v):
        return math.degrees(math.atan(v))
    print('  THE STEEPEST FACE, same grid, same operator, only r changed:')
    print('    linear (waves 1-4)      max |grad eta| %.4f  = %5.2f deg'
          % (s0.max(), deg(s0.max())))
    print('    nonlinear (wave 5)      max |grad eta| %.4f  = %5.2f deg   '
          'x%.3f' % (s.max(), deg(s.max()), s.max() / s0.max()))
    print('    p99.9 linear / nonlinear               %.4f / %.4f  = %5.2f / '
          '%5.2f deg' % (np.percentile(s0, 99.9), np.percentile(s, 99.9),
                         deg(np.percentile(s0, 99.9)),
                         deg(np.percentile(s, 99.9))))
    print('    Stokes 120 deg corner   %.4f  = %5.2f deg   <- the cap on ANY '
          'wave of permanent form' % (corner, B.STOKES_FACE_DEG))
    print('    section A needs         %.4f  = %5.2f deg = 90 - asin(1/n)'
          % (need, deg(need)))
    print('    -> reached %.2f deg. Short of the corner by %.2f deg and of '
          'section A by %.2f deg.' % (deg(s.max()), B.STOKES_FACE_DEG
                                      - deg(s.max()), deg(need) - deg(s.max())))
    return dict(lin=float(s0.max()), nl=float(s.max()), need=float(need),
                corner=float(corner), clamped=float(w.r2_clamped),
                ur_med=float(np.median(Ur)), ur_max=float(Ur.max()),
                r_max=float(r.max()), r_raw_max=float(rr.max()),
                past=float(np.mean(Ur > B.URSELL_STOKES_LIMIT)))


def chord_report(w, cam, t=0.0):
    """WHAT THE STEEPENING BOUGHT OPTICALLY, which is the only reason to do it.

    Section A is "the colour is the path", so the quantity is the PATH: the
    chord a view ray cuts through a wave before it comes out the far side. It
    is not the face slope -- the slope is what MAKES the chord possible -- and
    `through_face` already measures it by marching the refracted ray, so this
    reads the render's own instrument rather than a new one.

    Run on the same camera with r on and r off, so the pair differs in one
    field. THE ABSOLUTE NUMBER IS REPORTED AS WELL AS THE RATIO, because wave
    4's own retrospective names a guard that compared ratios and could not see
    a factor multiplying both terms.
    """
    out = {}
    for tag in ('nonlinear', 'linear'):
        keep = w.r2
        if tag == 'linear':
            w.r2 = np.zeros_like(w.r2)
        hit = trace(cam, w, t)
        P = cam.pos[None, None] + hit['D'] * hit['t_water'][..., None]
        m = hit['water'] & np.isfinite(hit['t_water'])
        # confine to the near field: beyond a few hundred metres one pixel is
        # many wavelengths and the chord is a sub-pixel statistic, not a path.
        rng = np.linalg.norm(P - cam.pos[None, None], axis=-1)
        m = m & (rng < 400.0)
        sh = shade_water(w, P, hit['D'], t)
        w.r2 = keep
        ch = sh['chord'][m]
        L = sh['L_path'][m]
        gx = 2.0 * L[..., 1] / np.maximum(L[..., 0] + L[..., 2], 1e-12)
        lit = ch > 0.02
        out[tag] = dict(
            n=int(m.sum()), frac=float(np.mean(ch > 0.02)),
            med=float(np.median(ch[lit])) if lit.any() else 0.0,
            p99=float(np.percentile(ch, 99.9)), mx=float(ch.max()),
            green=float(np.median(gx[lit])) if lit.any() else float('nan'),
            L_med=float(np.median(L[lit, 1])) if lit.any() else 0.0)
    print('THE PATH THROUGH THE FACE, from the render\'s own march '
          '(`through_face`):')
    print('    %-10s  pixels-with-a-chord   median chord   p99.9   max     '
          'median 2G/(R+B) of term 4' % '')
    for tag in ('linear', 'nonlinear'):
        o = out[tag]
        print('    %-10s  %8.4f              %7.3f m     %5.3f  %6.3f   %s'
              % (tag, o['frac'], o['med'], o['p99'], o['mx'],
                 ('%.4f' % o['green']) if o['green'] == o['green'] else '-'))
    a, b = out['linear'], out['nonlinear']
    if a['frac'] > 0 or b['frac'] > 0:
        print('    -> the steepening multiplies the lit fraction by %.2f and '
              'the median chord by %.2f'
              % (b['frac'] / max(a['frac'], 1e-12),
                 b['med'] / max(a['med'], 1e-12)))
    else:
        print('    -> NEITHER SURFACE PRODUCES A SINGLE THROUGH-PATH IN THIS '
              'FRAME, and that is the result.')
        print('       The refracted view ray dives at (90 - alpha) - '
              'asin(cos(alpha + delta)/n) below the horizontal -- 34 deg at '
              'the linear')
        print('       surface\'s 8 deg face and 28 deg at the nonlinear '
              'surface\'s 16 deg one -- while the crest it must cross falls '
              'at')
        print('       16 deg at most. The ray reaches the deep column before '
              'it reaches the far side, at every pixel, and no amount of '
              'water')
        print('       chemistry changes that. It is the 41.48 deg criterion '
              'measured on the render rather than argued from the geometry.')
    return out


# ============================================================== the cuvette
# BAR SECTION A CALLS THE WAVE FACE "A VARIABLE-PATH CUVETTE -- thin at the lip,
# thick toward the trough, with the colour grading across it", and asks the
# render to reproduce THE GRADE rather than the hue. So this renders the
# cuvette: a wedge of THIS SCENE'S WATER, 4 m across, its thickness ramping
# linearly from 0 at the top to 3 m at the bottom, standing in the same sun.
#
# IT IS A STAND-IN AND THE FIGURE'S CAPTION SAYS SO, exactly as wave 1 said so
# for the stamped rip channels and wave 3 for their absence. What it is standing
# in for is a face steeper than 41.4 degrees, which `face_slope_report` above
# measures this scene as unable to produce.
#
# EVERYTHING ELSE IN IT IS THE SCENE'S OWN: the same `iops()`, the same sun,
# the same `optics.fresnel` on both faces, the same `optics.refract` with its
# TIR branch, the same `through_path`. Nothing is tinted, nothing is chosen.
CUV_W, CUV_H = 4.0, 2.2         # m, the wedge's width and height
CUV_T = 3.0                     # m, thickness at the bottom; 0 at the top


def render_cuvette(back=True, res=(560, 620), spm=0.0):
    """The wedge, from due east. `back=True` puts the sun BEHIND it (the bar's
    backlit face); `back=False` moves the CAMERA to the sun's own side, so the
    same wedge is front-lit by the same sun and the glow has no forward
    direction to scatter into. The sun does not move between the two -- only the
    observer does, which is the honest way to run this control with one derived
    illuminant.

    TWO TERMS AND THEY ARE DIFFERENT PHYSICS.

      1  WHAT IS BEHIND IT, attenuated. The sky the view ray would have seen if
         the water were not there, times exp(-c L). For this water that is the
         dominant term, and it is the term bar section A is describing when it
         says the colour is the path.
      2  THE FORWARD GLOW. The sun's own beam, refracted into the wedge and
         single-scattered toward the eye through the Henyey-Greenstein lobe
         whose g was DERIVED from chapter 28's forward-dominance ratio. Looking
         west the scattering angle is 21 deg and the lobe is at its peak;
         looking east it is 159 deg and the same lobe is four orders down. That
         asymmetry, and not a lighting switch, is what makes the backlit panel
         backlit.
    """
    nw, nh = res
    u = (np.arange(nw) + 0.5) / nw * CUV_W - CUV_W / 2.0
    v = CUV_H * (1.0 - (np.arange(nh) + 0.5) / nh)      # metres above the base
    U, V = np.meshgrid(u, v)
    thick = CUV_T * (1.0 - V / CUV_H)                   # thin at the lip
    io = BO.iops(spm=spm)
    c = io['a'] + io['b']

    # the view: horizontal, along -x looking west (back=True) or +x looking east
    D = np.array([-1.0, 0.0, 0.0]) if back else np.array([1.0, 0.0, 0.0])
    nfront = -D                                         # front face's outward
    nback = D                                           # back face's outward
    Rf = OPT.fresnel(1.0)                               # normal incidence
    # 1 -- what is behind the wedge: the sky the ray continues into
    L_behind = ATM.sky(np.array([D[0]]), np.array([D[1]]),
                       np.array([0.02]))[0]
    L_tr = (1.0 - Rf) ** 2 * L_behind * np.exp(-c * thick[..., None])
    # 2 -- the sun's beam, refracted through the back face, scattered forward
    cos_in = max(float(np.dot(-SUN, -nback)), 0.0)      # on the back face
    if cos_in > 0.0:
        t = np.array(OPT.refract(-SUN[0], -SUN[1], -SUN[2],
                                 nback[0], nback[1], nback[2],
                                 1.0 / OPT.IOR[1]))
        t = t / max(float(np.linalg.norm(t)), 1e-12)
        cos_sc = float(np.dot(t, -D))                   # beam -> toward the eye
        E_beam = ATM.E_SUN * cos_in * (1.0 - OPT.fresnel(cos_in))
    else:
        cos_sc, E_beam = -1.0, np.zeros(3)
    L_gl = BO.forward_glow(E_beam, thick, cos_sc, io['a'], io['b']) * (1 - Rf)
    # 3 -- the front face's own reflection of the sky behind the OBSERVER
    L_ref = ATM.env_diffuse(np.array([-D[0]]), np.array([-D[1]]),
                            np.array([0.25]))[0] * Rf

    L = L_tr + L_gl + L_ref[None, None]
    outside = (np.abs(U) > CUV_W / 2.0 - 0.02)
    L = np.where(outside[..., None], (SAND_DRY * E_DOWN_AIR / np.pi)[None, None],
                 L)
    return dict(L=L, thick=thick, Lp=L_tr + L_gl, L_tr=L_tr, L_gl=L_gl,
                L_ref=L_ref, cos_sc=cos_sc, back=back, mask=~outside, io=io)


def cuvette_report(cvA, cvB):
    """The numbers section A asks for, all scene-linear, all within-frame.

    THE INSTRUMENT IS THE TRANSMITTANCE AND NOT THE RADIANCE. A green excess
    measured on the radiance mixes the water's colour with the SOURCE's colour,
    and the two panels here have different sources by construction -- one looks
    into the western sky and one into the eastern. Dividing every pixel by the
    zero-path pixel of its OWN panel removes the source exactly, which is the
    same cancellation the cuvette itself runs on, and leaves a number that is 1
    when there is no water and departs from 1 only through the path.
    """
    io = cvA['io']
    a_, b_ = io['a'], io['b']
    th, m = cvA['thick'], cvA['mask']
    j = th.shape[1] // 2
    col = th[:, j]

    def _T(cv, key='L'):
        z = cv[key][int(np.argmin(col)), j]
        return cv[key] / np.maximum(z, 1e-12)

    print('  -- A1, THE COLOUR IS THE PATH: 2G/(R+B) of the TRANSMITTANCE')
    TA, TB = _T(cvA), _T(cvB)
    out = {}
    for nm, T, cv in (('backlit  (sun behind the water)', TA, cvA),
                      ('front-lit (sun behind the camera)', TB, cvB)):
        g_thick = float(np.median(green_excess(T[m & (th > 2.0)])))
        g_thin = float(np.median(green_excess(T[m & (th > 0.05) & (th < 0.25)])))
        out[nm[:4]] = (g_thin, g_thick)
        print('     %-34s thin %.4f   thick %.4f   grade %.4f'
              % (nm, g_thin, g_thick, g_thick / g_thin))
    print('     the GRADE is the same in both panels because it is the PATH, '
          'and the path\n     does not know where the sun is. What differs is '
          'the forward glow:')
    gl = cvA['L_gl'][m & (th > 2.0)]
    lt = cvA['L'][m & (th > 2.0)]
    print('        backlit   scattering angle %.1f deg, HG lobe %.4g /sr, '
          'glow = %.2f%% of the pixel'
          % (math.degrees(math.acos(np.clip(cvA['cos_sc'], -1, 1))),
             float(BO.hg_phase(BO.PHASE_G, cvA['cos_sc'])),
             100 * float(np.median(gl[:, 1] / lt[:, 1]))))
    print('        front-lit scattering angle %s, glow = %.2f%% -- the sun '
          'cannot reach the\n                  back face at all, so the term '
          'is identically zero'
          % ('n/a (unlit face)',
             100 * float(np.median(cvB['L_gl'][m & (th > 2.0)][:, 1]
                                   / cvB['L'][m & (th > 2.0)][:, 1]))))

    print('  -- A2, THE GREEN VANISHES WHEN THE PATH DOES')
    grade = []
    for lo, hi in ((0.0, 0.02), (0.05, 0.15), (0.3, 0.5), (0.9, 1.1),
                   (1.9, 2.1), (2.8, 3.0)):
        mm = m & (th >= lo) & (th <= hi)
        if mm.sum() < 10:
            continue
        g = float(np.median(green_excess(TA[mm])))
        grade.append((0.5 * (lo + hi), g))
        print('     path %5.2f m   transmittance 2G/(R+B)  %.4f' % (
            0.5 * (lo + hi), g))
    print('     at zero path it is 1.0000 by construction and by physics: the '
          'transmitted\n     spectrum IS the source spectrum. Nothing in this '
          'file can tint it.')

    print('  -- A3, the cuvette inverted, term by term: c = -ln(T2/T1)/(L2-L1)')
    print('     and the DECOMPOSITION is the finding -- each term added is a '
          'different\n     way for a real frame to lie to this instrument.')
    for (l1, l2) in ((0.25, 1.0), (0.5, 2.5), (1.0, 3.0)):
        i1 = int(np.argmin(np.abs(col - l1)))
        i2 = int(np.argmin(np.abs(col - l2)))
        print('     L1 = %.2f m, L2 = %.2f m' % (col[i1], col[i2]))
        for key, nm in (('L_tr', 'transmitted only  '),
                        ('Lp', '+ the forward glow'),
                        ('L', '+ the front face  ')):
            ch = BO.cuvette_c(cvA[key][i1, j], cvA[key][i2, j],
                              col[i1], col[i2])
            print('        %s c = %s   err %s %%'
                  % (nm, np.round(ch, 5),
                     np.round(100 * (ch / (a_ + b_) - 1), 2)))
    print('     put in                  c = a + b = %s' % np.round(a_ + b_, 5))
    print('     WHY THE GLOW BIASES IT LOW: the glow goes as L exp(-cL), not '
          'as exp(-cL),\n     so -ln(T2/T1)/(L2-L1) picks up -ln(L2/L1)/(L2-L1) '
          '= %.4f m^-1 weighted by\n     the glow\'s share of the signal. It '
          'is worst in the GREEN, which is the band\n     the whole colour '
          'argument lives in.'
          % (-math.log(3.0 / 1.0) / 2.0))

    print('  -- A4, what the cuvette CANNOT do, and what closes it')
    print('     transmission alone gives a + b and nothing else. Paired with '
          'the same\n     water\'s DEEP REFLECTANCE it separates a from b_b, '
          'and the Babin bridge then\n     gives the mineral load. Run on two '
          'waters:')
    for nm, spm in (('the water mass, offshore', 0.0),
                    ('a surf-zone layer', 500.0)):
        iot = BO.iops(spm=spm)
        inv = BO.invert_a_bb(iot['a'] + iot['b_b'],
                             BO.volume_reflectance(iot['a'], iot['b_b'], 60.0))
        print('     %-24s a   %s -> %s' % (nm, np.round(iot['a'], 4),
                                           np.round(inv['a'], 4)))
        print('     %-24s SPM put in %7.1f  ->  recovered %s mg/L'
              % ('', spm, np.round(inv['spm'], 2)))
    print('     the a-PARTITION stays open: three constituents, three bands, '
          'and CDOM and\n     mineral absorption are too collinear to separate '
          'with them. Closing it needs\n     a fourth band or a second '
          'geometry, and that is named rather than attempted.')
    return dict(grade=grade, panels=out)


def bay_ladder(L, ex, w):
    """Bar section J's colour ladder, measured on the render's own buffer.

    Five surfaces, one exposure: deep blue offshore, teal over the shallows,
    white surf, wet sand, dry sand. J says the wet/dry pair is the trustworthy
    one because the two are close in level; it is the pair reported first."""
    mw, ml = ex.get('water_mask'), ex.get('land_mask')
    if mw is None or ml is None:
        return
    P = ex['water_P']
    dep = w.sample(P[..., 0], P[..., 1], w.d)
    brk = w.sample(P[..., 0], P[..., 1], w.brk.astype(float))
    Lw = L[mw]
    print('  -- bar J\'s colour ladder, scene-linear radiance (R, G, B)')
    for nm, sel in (('deep, d > 5 m', dep > 5),
                    ('mid, 2 < d < 5 m, unbroken', (dep > 2) & (dep < 5)
                     & (brk < 0.2)),
                    ('shallow, d < 2.5 m, unbroken', (dep < 2.5) & (brk < 0.2)),
                    ('surf, breaking', brk > 0.8)):
        if sel.sum() > 30:
            v = np.median(Lw[sel], 0)
            print('     %-30s %s   2G/(R+B) %.4f'
                  % (nm, np.round(v, 4), 2 * v[1] / max(v[0] + v[2], 1e-9)))
    Pl = None
    hl = None
    print('     (wet/dry sand pair: albedo ratio %s, from optics.wet_albedo, '
          'no new constant)' % np.round(SAND_WET / SAND_DRY, 4))


def cliff_edge(w, y_cam, top=12.0, back=2.0):
    """Where a camera can actually stand, on the row it is standing on.

    THE FIRST FRAMING OF THIS FILE PUT BOTH CAMERAS AT A FIXED x = 694 m AND
    RENDERED A FIELD. The cliff top is not at one x: wave 3's coastal loop
    retreats the shore by different amounts at different y, so the brow runs
    from x = 632 to x = 680 across the domain and a camera 60 m inland of it
    looks at the coastal plain and nothing else. Standing at the brow is a
    property of the LANDFORM and has to be read off the bed, not assumed."""
    j = int(np.argmin(np.abs(w.y - y_cam)))
    i = int(np.argmax(w.h[j] > top))
    xc = float(w.x[i]) + back
    return xc, float(w.sample(np.array([xc]), np.array([y_cam]), w.h)[0])


def horizon_check(L, cam, edge_frac=0.12):
    """Bar section K2: the sea's radiance at grazing must approach the sky's
    reflected value CONTINUOUSLY, and a seam there is a tell at a glance."""
    D = cam.rays()
    up = D[..., 2] >= 0.0
    full = np.where(up.all(1))[0]
    if full.size == 0 or full[-1] + 4 >= L.shape[0] or full[-1] < 3:
        print('  -- horizon not in frame')
        return
    j = int(full[-1])
    n = L.shape[1]
    k = max(int(edge_frac * n), 2)
    print('  -- the sea-sky horizon (bar K2)')
    # OFF THE PATH FIRST, and that is the only place the question can be asked.
    # Down the sun's own azimuth the sea just below the horizon carries the
    # GLITTER, whose radiance is the sun's image and is two orders above the
    # sky: comparing those two is measuring the glitter, not the seam. The
    # frame's outer columns are 15-17 deg off the path's centre and outside its
    # half-width, and that is where the continuity criterion lives.
    for nm, sel in (('off the path (frame edges)',
                     np.r_[0:k, n - k:n]),
                    ('down the path (frame centre)',
                     np.arange(n // 2 - k // 2, n // 2 + k // 2))):
        a = L[j - 3:j - 1, sel].reshape(-1, 3).mean(0)
        b = L[j + 1:j + 3, sel].reshape(-1, 3).mean(0)
        print('     %-28s sky %s  sea %s  ratio %s'
              % (nm, np.round(a, 4), np.round(b, 4),
                 np.round(b / np.maximum(a, 1e-9), 4)))


if __name__ == '__main__':
    main()
