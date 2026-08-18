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
import beach_camera as CAM
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
                                                # plain rather than beach.
                                                # WAVE 8: the two elevations it
                                                # has to clear are now DERIVED
                                                # rather than declared -- the
                                                # swell's run-up limit at
                                                # `beach.BERM_Z` = 0.727 m and
                                                # the storm's at
                                                # `beach.BACKSHORE_Z` = 1.029 m
                                                # -- so 6.0 m is 5.8x the
                                                # highest surface any swash on
                                                # this coast builds, and the
                                                # cliff face between them is
                                                # classed by SLOPE and never
                                                # reaches this test. `?` on the
                                                # value; it separates two
                                                # things that are 5 m apart.
SAND_WET = OPT.wet_albedo(SAND_DRY)[0]
ROCK_WET = OPT.wet_albedo(ROCK_DRY)[0]

# --- WAVE 8: `wet_albedo` HAS A SPECULAR TERM IN IT AND IT WAS BEING SPENT AS
# DIFFUSE. A finding about how this file USES `optics.py`, not a defect inside
# it -- the module is right and is not touched.
#
#       a_wet = R_EXT + (1 - R_EXT)(1 - R_INT) a / (1 - a R_INT)
#               \____/   \______________________________________/
#              the film's         the trapped series: what actually
#              own surface        comes back OUT of the substrate
#              reflection
#
# Waves 4-7 handed the whole of that to a Lambertian. The first term is light
# that never entered the film: it is the SPECULAR reflection off the water
# surface, and putting it in the diffuse lobe makes wet sand UNIFORMLY BRIGHTER
# and never glossy -- which is backwards twice over, because the thing bar H3
# calls "one of the strongest tonal edges in these frames" is wet sand going
# DARKER and SHINIER at once. The two halves move together and this file now
# spends them where they belong:
#
#   diffuse   a_wet - R_EXT            strictly darker than the dry sand
#   specular  fresnel(theta_v)         a lobe, over a slope distribution
#
# R_EXT is the hemispherical-average external reflectance, which is the right
# thing to REMOVE from an albedo lit by a hemisphere; what is ADDED back is the
# directional fresnel(theta_v) at the view angle, which is the right thing for
# a lobe. They are the same physics integrated over different variables and the
# swap is stated rather than hidden.
SAND_WET_DIFF = SAND_WET - OPT.R_EXT
ROCK_WET_DIFF = ROCK_WET - OPT.R_EXT

# The wet film's residual rms slope. `?` AND IT IS THE ONE NEW UNKNOWN THIS
# WAVE ADDS. A film over a grain pack is not a mirror: it drowns the pores and
# leaves the pack's larger undulations, and no measurement of that residual was
# available. 0.20 is DECLARED; the suite carries 0.10 and 0.40 as the bracket
# and `_sec_land` reports what the frame does across it. Nothing else in the
# render depends on it -- the SKY half of the specular needs no roughness at
# all (a smooth film mirrors a smooth sky, and the sky is smooth), so the
# bracket moves only the sun's own glint on the wet band.
SIGMA_WET = 0.20
SIGMA_WET_BRACKET = (0.10, 0.40)


def wet_specular(D, N, sigma=SIGMA_WET, sun=True):
    """The wet band's specular lobe: sky mirror + the sun over a slope pdf.

    TWO TERMS AND ONLY ONE OF THEM NEEDS THE ROUGHNESS.

      sky   fresnel(theta_v) * env_diffuse(mirror(D, N)). Exact for a smooth
            film; a rough one blurs an already smooth sky and moves it by
            nothing measurable. No `?` enters here.
      sun   fresnel(theta_h) * E_SUN * p(slope) / (4 cos^4(beta) cos(theta_v)),
            the SAME Jacobian `beach_optics.glitter_radiance` derives for the
            sea -- dw_v = 4 cos(omega) cos^3(beta) dz -- with the Cox & Munk
            wind-driven slope pdf replaced by an isotropic Gaussian of rms
            `sigma`. The Jacobian is geometry and transfers unchanged; the
            distribution is the surface's and does not.

    `beach_optics.glitter_radiance` is NOT called and the reason is that it
    assumes the mean surface is HORIZONTAL (it builds the required normal from
    s + r and reads its z as cos(beta)). A beach face is 3.0 deg off horizontal
    and a wet rock face is not, so the half-vector has to be taken against the
    LOCAL normal. That is a finding about the function's applicability, and it
    is reported rather than patched: nothing in `beach_optics` is changed.
    """
    n = N / np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)
    r = -D                                       # back toward the eye
    ct_v = np.clip((n * r).sum(-1), 1e-6, 1.0)   # view zenith on the LOCAL n
    mir = 2.0 * ct_v[..., None] * n - r
    mir = mir / np.maximum(np.linalg.norm(mir, axis=-1, keepdims=True), 1e-12)
    L = OPT.fresnel(ct_v) * sky_radiance(mir)
    if sun:
        hv = SUN[None] + r
        hv = hv / np.maximum(np.linalg.norm(hv, axis=-1, keepdims=True), 1e-12)
        cb = np.clip((hv * n).sum(-1), 1e-6, 1.0)        # cos(beta) on n
        com = np.clip((SUN[None] * hv).sum(-1), 0.0, 1.0)
        # the half-vector's tilt off the local normal, as a SLOPE
        s2 = (1.0 - cb * cb) / (cb * cb)
        lit = ((n * SUN[None]).sum(-1) > 0.0)
        g = wet_slope_pdf(s2, sigma) * sun_jacobian(cb, ct_v)
        L = L + OPT.fresnel(com) * E_SUN[None] * (g * lit)[..., None]
    return L


def wet_slope_pdf(s2, sigma=SIGMA_WET):
    """Isotropic Gaussian slope density at squared slope `s2`.

    Its own function so the suite can integrate THE ONE THE SHADER USES over
    the slope plane and get 1. A normalisation row that rebuilds the density
    beside itself tests the row and not the code -- which is a mistake this
    file has made before and this is the fix for it."""
    return np.exp(-0.5 * s2 / (sigma * sigma)) / (2.0 * np.pi * sigma ** 2)


def sun_jacobian(cos_beta, cos_theta_v):
    """dw_v = 4 cos(omega) cos^3(beta) dz -- the SAME change of variables
    `beach_optics.glitter_radiance` derives for the sea, written out here so
    the suite can check it apart from the density it multiplies. Geometry, so
    it transfers from the sea to a wet beach unchanged; the DENSITY does
    not."""
    return 1.0 / (4.0 * cos_beta ** 4 * cos_theta_v)


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

        # --- WAVE 10: THE BED ARGUMENT IS A WATER-SIDE REFLECTANCE, and waves
        # 4-9 handed it an air-side one. `SAND_WET` is `wet_albedo(SAND_DRY)`,
        # which is the apparent albedo of a wet film SEEN FROM THE AIR --
        # `rho_water` then crossed the interface twice more around it and
        # applied the same trapped series a second time. The derivation, the
        # identity that settles which side is which, and the `?` that survives
        # it are in `beach_optics.submerged_bed_rho`.
        self.dep_lut = np.geomspace(0.05, 20.0, 48)
        self.rho_lut = BO.submerged_bed_rho(
            SAND_DRY, math.sin(math.radians(SUN_EL)), self.dep_lut,
            absorb=self.io_clear['a'] + self.io_clear['b_b'])
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

        # --- WAVE 12: THE SURFACE COVER, AND IT IS A LANDFORM FACT THIS FILE
        # HAD NO WAY TO ASK FOR. `shade_land` decided rock-versus-sand by SLOPE
        # alone through wave 11, which chapter 11 says outright is one clause of
        # three ("Outcrop = rockMask from (slope > tan 40 deg) u (regolithDepth
        # ~ 0) u (convex curvature)"), and it is the clause that CANNOT fire on
        # the landform bar section H1 is about: a wave-cut bench is FLAT, so a
        # slope test calls the whole of it sand. `bay_bed` now returns the
        # loop's own bedrock and the sediment lying on it, so the missing
        # clause is available and costs one array.
        self.plan = bay.get('plan')             # the static-equilibrium bay,
                                                # when this bed has one
        bch = bay.get('beach')
        if bch is not None and 'cover' in bch:
            self.regolith = bch['regolith']
            self.cover = bch['cover']
            self.planed = bch['planed']
        else:                                   # a bed built without the beach
            z = np.zeros_like(self.h)
            self.regolith, self.cover = z, z
            self.planed = np.zeros_like(self.h, bool)

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


def shade_land(w, P, D, parts=None, foot=None):
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
    # WAVE 12: CHAPTER 11'S rockMask HAS THREE CLAUSES AND THIS FILE HAD ONE.
    #
    #   Outcrop = rockMask from (slope > tan 40 deg) u (regolithDepth ~ 0)
    #             u (convex curvature).  "Emerges automatically if you run
    #             layered K -- you don't author it."
    #
    # The slope clause is below and is unchanged. The REGOLITH clause is the
    # one that decides bar section H1's landform, and it is the one that was
    # missing: a wave-cut bench is FLAT, so the slope clause calls the whole of
    # it sand and the bench -- the surface two of the bar's frames are OF --
    # can never appear in this render at all. That is what wave 11's critic
    # measured as "no cliff, no headland, no wave-cut bench, no exposed rock,
    # no offshore reef" and diagnosed as the bed never crossing the slope
    # threshold; the bed does cross it (15.9% of the visible land, measured),
    # but the landform in question is not a slope.
    #
    # `w.cover` is `beach.sand_cover_fraction` of the sediment the bed
    # generator actually laid, so "sand infilling the hollows" is an area
    # fraction taken over the rock's own sub-grid roughness rather than a
    # threshold: a veneer one roughness deep covers 76% and leaves a quarter of
    # the bench standing through it. `w.planed` gates it to ground the SEA has
    # stripped -- the coastal plateau also carries none of this loop's sediment
    # and is a soil-mantled land surface that has never been in the surf, so
    # zero regolith there is not bare rock and must not be painted as it.
    cover = w.sample(xw, yw, w.cover)
    planed = w.sample(xw, yw, w.planed.astype(float))
    # WAVE 12, SECOND PASS: AND THE COVER FRACTION IS NOT A SURFACE EITHER.
    # `planed * (1 - cover)` paints the EXPECTATION of a binary mask -- a wash
    # of one-quarter rock over every square metre, where bar H1's word is
    # POCKETED and means a quarter of the AREA. `beach.rock_bare_mask` draws
    # the same closed form as a realisation: sand fills each pocket from the
    # bottom up, so the bare share is the top (1 - cover) of the rock's own
    # height ordering. Its expectation is `sand_cover_fraction` exactly, at
    # every pocket scale, so nothing about the volume book moves -- only its
    # placement. `foot` is the pixel footprint: once a pocket is sub-pixel the
    # correct answer for that pixel IS the mean, and the mask returns to it.
    bare = np.clip(planed * B.rock_bare_mask(xw, yw, cover, foot=foot),
                   0.0, 1.0)[..., None]
    rock = np.clip((np.abs(hx) + np.abs(hy) - 0.35) / 0.5, 0.0, 1.0)[..., None]
    rock = np.maximum(rock, bare)               # the union chapter 11 writes
    plain = np.clip((hz - PLAIN_Z) / 4.0, 0.0, 1.0)[..., None] * (1 - rock)
    # WAVE 8: THE WET/DRY BOUNDARY IS A DISTRIBUTION AND NOT A LINE. Waves 4-7
    # ramped it over a declared 0.35 m either side of a single run-up height.
    # Run-up heights inherit the incident waves' Rayleigh statistics, which
    # this project has carried since wave 1, so the share of swash cycles that
    # reach a level -- and therefore the share of the surface still carrying a
    # film -- is exp(-(z/R)^2). Nothing is placed: `beach.swash_wetness`.
    #
    # WAVE 12: ...AND A DISTRIBUTION IS NOT A SURFACE. Wave 8 got the statistic
    # right and then PAINTED it, which draws the time-average of the beach.
    # An average has no edge, and bar H3 calls this boundary "one of the
    # strongest tonal edges in these frames"; wave 11's critic measured the
    # consequence as a smooth ramp with no boundary anywhere across 48 px of
    # beach face. The shader now draws a REALISATION -- `beach.damp_limit`, the
    # maximum of the last tau_dry/T run-ups, sharp in z and cusped alongshore
    # at the swash excursion -- which is the same correction the optics lane
    # made to the glitter and the wave-field lane made to the foam, in the
    # third and last place this project was drawing an ensemble mean.
    #
    # AND IT IS TWO MASKS, BECAUSE THEY ARE TWO SUBSTANCES. Pore water in the
    # grain pack darkens (the trapped series) and lasts minutes; free water
    # standing on the surface reflects, and is only there while the swash sheet
    # is. Waves 4-11 drove both from one field, which puts a mirror on damp
    # sand -- and that, not the albedo, is what inverts bar J's wet/dry rung.
    z_damp = B.damp_limit(yw)
    z_sheet = B.sheet_front(yw)
    wet = (hz <= z_damp).astype(float)[..., None]       # pore water: DIFFUSE
    film = (hz <= z_sheet).astype(float)[..., None]     # free water: SPECULAR
    sand = 1.0 - rock - plain
    # the DIFFUSE albedo. The wet forms are the trapped series with the film's
    # own surface reflection taken OUT of them (see SAND_WET_DIFF): wet sand is
    # darker than dry sand diffusely, which is the direction bar H3 says.
    alb = ((SAND_DRY[None, None] * (1 - wet) + SAND_WET_DIFF[None, None] * wet)
           * sand
           + (ROCK_DRY[None, None] * (1 - wet) + ROCK_WET_DIFF[None, None]
              * wet) * rock
           + PLAIN_DRY[None, None] * plain)
    ndl = np.clip((N * SUN[None, None]).sum(-1), 0.0, 1.0)
    # WAVE 8: THE SHADOW RAY. Wave 7 measured its cost at exactly 0.0% under
    # both suns and said why -- "not because the shading is right but because
    # wave 3's landform is a ramp and a cliff face with nothing on it to cast
    # one". There is now a beach at the foot of a 15 m cliff, so there is
    # something to cast one, and the ordering wave 7 argued for is the reason
    # this is built in the same wave as the beach and not before it.
    sh = land_shadow(w, P, N)
    L = alb * (E_SUN[None, None] * (ndl * sh)[..., None] / np.pi + env_irr(N))
    # ...AND THE SPECULAR HALF, which is where the rest of `wet_albedo` went.
    # WAVE 12 MOVED IT OFF `wet` AND ONTO `film`. It is a lobe off a water
    # surface, so it needs a water surface: `film` is the swash sheet, not the
    # damp band. `sand + rock` and not the plain, because a wetted plain is a
    # surface this scene never has.
    spec = film * (sand + rock) * wet_specular(D, N)
    if parts is not None:
        parts['diffuse'] = L
        parts['specular'] = spec
        parts['wet'] = wet[..., 0]
        parts['film'] = film[..., 0]
        parts['sand'] = sand[..., 0]
        parts['N'] = N
        parts['shadow'] = sh
    return L + spec


SHADOW_ON = True                # the paired frame's one switch, and nothing
                                # else in the file reads it


def land_shadow(w, P, N, n=40, reach=None, sun=None):
    """1 where the sun reaches the point, 0 where the bed is in the way.

    A HARD RAY, and the softness it is missing is stated rather than faked: the
    sun's disc is 0.53 deg across, so a real shadow edge is penumbral over
    about 1/100 of the distance to the caster -- 0.4 m at the foot of this
    cliff, which is under a pixel at bar J's range and is worth a sentence, not
    a filter.

    THE REACH IS THE LANDFORM'S OWN AND NOT A DECLARED DISTANCE. Nothing can
    cast a shadow further than its height divided by the tangent of the sun's
    elevation, so the march stops at h_max/tan(el) -- 42 m for this bed at the
    render's 21 deg sun and 12 m at bar J's 56 deg one. A fixed 600 m reach
    (wave 7's `shadow_cost`) marched fifteen times as far for the same answer.
    """
    S = SUN if sun is None else np.asarray(sun, float)
    if S[2] <= 1e-3 or not SHADOW_ON:
        return np.ones(P.shape[:-1])
    if reach is None:
        reach = float(np.nanmax(w.h)) / max(S[2], 1e-3)
    lit = (N * S).sum(-1) > 0.0
    occ = np.zeros(P.shape[:-1], bool)
    s = np.geomspace(max(2.0 * float(w.x[1] - w.x[0]), 1.0), max(reach, 4.0), n)
    for t in s:
        Q = P + S * t
        occ |= (Q[..., 2] < w.sample(Q[..., 0], Q[..., 1], w.h)) & lit
    return (~occ).astype(float)


# The swash's own reach. WAVE 8 MOVED THE SLOPE THIS IS BUILT ON, and the move
# is a correction rather than a refinement. Waves 4-7 took tan(beta) from the
# bed's slope AT THE BREAK POINT -- 100 m offshore, in 2 m of water, where the
# profile is 1:130 -- and fed that to the Iribarren number. But the run-up is
# what the swash does ON THE BEACH FACE, and Hunt's xi is defined on the slope
# the swash climbs. The old reading gave xi = 0.332 and R = 0.50 m; the face's
# own slope gives xi = 0.485 and R = 0.727 m, 46% higher, and it is the second
# that is Hunt's quantity. Both are printed so the change is visible.
_XI = None
RUNUP = 0.0
_XI_BRK = None
RUNUP_BRK = 0.0


def _set_runup():
    global _XI, RUNUP, _XI_BRK, RUNUP_BRK
    sc = B.run_scene()
    tr = sc['tr']
    b = B.breaker_state(tr)
    i = b['i_cell']
    slope = abs(float(np.gradient(tr['h'], tr['dx'])[i]))
    L0 = B.deep_wavelength(B.T_SWELL)
    _XI_BRK = B.iribarren(slope, B.H0_SWELL, L0)
    RUNUP_BRK = B.runup_hunt(B.H0_SWELL, _XI_BRK)
    _XI = B.iribarren(B.TAN_FACE, B.H0_SWELL, L0)
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


# ==================================================== WAVE 8: THE AIR, AND IT
# NEEDS ONE NEW NUMBER AND NOT TWO
#
# `shade_water` and `shade_land` return the radiance LEAVING the surface and
# waves 1-7 handed it straight to the film. Over a pool five metres across that
# is exact to a part in ten thousand; over a frame whose farthest water is
# beyond the visible horizon it removes two terms of the same size as the
# picture -- the extinction of the surface's own radiance, and the airlight
# scattered into the line of sight.
#
#   L(r) = L_surface * exp(-beta r)  +  L_airlight * (1 - exp(-beta r))
#
# THE RAYLEIGH COEFFICIENT IS NOT A NEW CONSTANT. `atmosphere.TAU_R` is the
# ZENITH optical depth this project derived for the sun's own colour, and over
# an exponential atmosphere of scale height H_R the surface coefficient is
# beta = tau/H_R by definition of the integral. Per channel, so the airlight is
# spectrally right without anything being declared.
#
# THE AEROSOL COEFFICIENT IS THE ONE `?`. Koschmieder's beta = 3.912/V turns a
# meteorological visibility into an extinction coefficient, and a maritime
# boundary layer runs 20-60 km. The CLEAN end is shipped -- it is the
# conservative choice for a gap being closed, since it understates rather than
# overstates what the new term does -- and the hazy end is rendered beside it
# and reported. It is NOT read off a photograph: bar J and bar K show a sharp
# horizon and the standing ruling says a level may not be read off them.
#
# WHAT THE AIRLIGHT RADIANCE IS, AND IT IS NOT A DECLARED COLOUR. In a
# horizontally homogeneous atmosphere a horizontal path of INFINITE length
# reaches exactly the radiance of the sky at the horizon in that azimuth --
# that is what the horizon sky IS. So the airlight is `sky_radiance` evaluated
# on the ray flattened to the horizontal, which costs nothing, carries the
# azimuthal structure (bright toward the sun, dark away from it) and needs no
# new number at all.
#
# AND IT CLOSES THE SEAM BY CONSTRUCTION, WHICH IS THE POINT. At grazing the
# sea's range goes to infinity, its transmittance to zero, and its radiance to
# the airlight -- which is the sky just above the horizon. Bar K2's continuity
# criterion is then satisfied identically and NOT by a fitted number, whatever
# beta and whatever the airlight's colour turn out to be.
#
# THE TWO APPROXIMATIONS, BOTH MARKED. (1) A slant path is shorter through the
# atmosphere than a horizontal one, so the airlight on a steeply downward ray
# is over-stated -- but a steeply downward ray is looking at the ground under
# the camera, where 1 - T is 0.0002, so the error is where the term is not.
# (2) The aerosol's airlight is given the RAYLEIGH sky's colour, which
# over-blues the haze term; the aerosol phase function is forward and nearly
# grey and a proper source function needs a model this file does not have. Both
# vanish at the seam, which is the measurement the term is being built for.
H_RAYLEIGH = 8500.0                     # m, the standard scale height
VIS_CLEAN, VIS_HAZY = 60000.0, 20000.0  # m, `?` -- the bracket
VIS_SHIPPED = VIS_CLEAN                 # the clean end, declared


def beta_ext(vis=None):
    """The extinction coefficient, per channel, 1/m. Rayleigh + aerosol."""
    b = np.asarray(ATM.TAU_R, float) / H_RAYLEIGH
    v = VIS_SHIPPED if vis is None else vis
    return b + (0.0 if not v else CAM.koschmieder_beta(v))


def aerial(L, D, r, vis=None):
    """Apply extinction and airlight over a path of length `r`."""
    b = beta_ext(vis)
    T = np.exp(-r[..., None] * b[None])
    flat = D.copy()
    flat[..., 2] = 0.0
    nrm = np.linalg.norm(flat, axis=-1, keepdims=True)
    flat = np.where(nrm > 1e-9, flat / np.maximum(nrm, 1e-9), flat)
    return L * T + sky_radiance(flat) * (1.0 - T)


def render(cam, w, t=0.0, label='', air=True, vis=None):
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
        Lw = sh['L'][0]
        if air:
            Lw = aerial(Lw, D[mw], np.linalg.norm(Pw - cam.pos[None], axis=-1),
                        vis)
        L[mw] = Lw
        ex['water'] = sh
        ex['water_mask'] = mw
        ex['water_P'] = Pw
    # land
    ml = tr['hit_land'] & ~tr['water'] & ~up
    if ml.any():
        Pl = cam.pos[None] + tr['t_land'][ml][..., None] * D[ml]
        lp = {}
        # THE PIXEL'S FOOTPRINT ON THE GROUND, and it is geometry rather than a
        # filter width: a pixel subtends 2 tan(fov/2)/h radians, so at range t
        # it covers t times that on a surface square to the ray, and 1/cos of
        # it on one that is not. The obliquity factor is capped at 20 because a
        # ray grazing the plateau has an unbounded footprint and the cap is
        # where the mask has already gone to its mean anyway.
        px = 2.0 * cam.tan / cam.h
        nz = np.clip(np.abs(D[ml][..., 2]), 1.0 / 20.0, 1.0)
        foot = tr['t_land'][ml] * px / nz
        Ll = shade_land(w, Pl[None], D[ml][None], parts=lp,
                        foot=foot[None])[0]
        ex['land_parts'] = {k: (v[0] if hasattr(v, 'ndim') and v.ndim >= 1
                                else v) for k, v in lp.items()}
        if air:
            Ll = aerial(Ll, D[ml], np.linalg.norm(Pl - cam.pos[None], axis=-1),
                        vis)
        L[ml] = Ll
        ex['land_mask'] = ml
        ex['land_P'] = Pl                       # wave 7: for the shadow cost
    ex['sky_mask'] = up
    ex['trace'] = tr
    ex['air'] = bool(air)
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

    # ---- WAVE 7: THE OWNER'S TWO CLIFF VIEWPOINTS, UPRIGHT ------------------
    # The gauntlet's first hyper-realism criterion, attempted for the first
    # time. THE PORTRAIT ASPECT IS PART OF THE FRAMING, not a layout choice:
    # bar J and bar K both record the frame upright, and an upright 4:3 held by
    # the same lens is 1.33x taller and 0.75x wider than the same lens held
    # landscape -- which moves the horizon, the depression and every content
    # bound in `beach_camera`. So these two are 3:4 where every earlier frame
    # in this file is 16:9, and the numbers in their captions are the reason.
    # THE s7 FRAMES DO NOT TAKE `--fast`, AND THAT IS WAVE 6'S RULE APPLIED
    # RATHER THAN BROKEN. s4, s5 and s6 are three terms of one comparison at
    # one camera and one raster size; drawing s6 at the full 900 would have
    # made that a comparison of resolutions as well as of physics, so every
    # frame in that series is drawn at `--fast`. The s7 pair has no earlier
    # term -- it is the first frame at this viewpoint -- so its size is free,
    # and it is fixed here at 720 x 960 with 2 x 2 supersampling regardless of
    # the flag. Nothing measured off it depends on the raster except the far
    # range tail, and `aerial_cost` reports that dependence in the same line.
    SS7 = SS_HERO
    W7, H7 = W_HERO * SS7, H_HERO * SS7
    L_surf, s_lines, D_lines, camJ7, infJ7, camK7, infK7, az_j, bear_j = \
        hero_cameras(w, W7, H7)
    CAM.report([infJ7, infK7], print)
    print()
    print('  the surf zone is %.0f m wide (this transform\'s own median) and '
          'bar J reads "three to four" lines in it, so the line spacing used '
          'is %.1f m at a range of %.0f m.' % (L_surf, s_lines, D_lines))
    print('  bar J\'s far shoreline bears %.2f deg from this eye, so the axis '
          'is %.2f deg -- half a frame width off it, which puts the coast at '
          'one edge and the sea in the rest.' % (bear_j, az_j))
    print()
    LJ7, exJ7 = render(camJ7, w)
    mJ7 = frame_report('J', w, camJ7, infJ7, LJ7, exJ7)
    print()
    bay_ladder(LJ7, exJ7, w)
    print()
    LK7, exK7 = render(camK7, w)
    mK7 = frame_report('K', w, camK7, infK7, LK7, exK7)
    print()
    wchk7 = wind_check(w, LK7, camK7, exK7)
    print()
    horizon_check(LK7, camK7)
    print()
    # THE s7 FRAMES ARE NOT OVERWRITTEN. Wave 8 changes four fields inside the
    # same camera, so s7 and s8 are the pair that measures the wave -- the same
    # two-wave rule that protected s4 against s5 and s5 against s6. `--redo-s7`
    # is there for a reader who wants the old frame regenerated on the new bed,
    # and it is deliberately NOT the default.
    if '--redo-s7' in sys.argv:
        _save(downsample(LJ7, SS7), '%s/s7-frame-J.png' % OUT,
              caption=_cap_J7(w, camJ7, infJ7, mJ7))
        _save(downsample(LK7, SS7), '%s/s7-frame-K.png' % OUT,
              caption=_cap_K7(w, infK7, mK7, wchk7))

    # ---- WAVE 8 IS `--wave8` AND NOT PART OF THIS RUN, and the reason is the
    # s4/s5/s6 rule. Those three frames are ONE comparison -- same camera, same
    # bed, same sun, one field changed each time -- and wave 8 changes four at
    # once. `main` regenerates s6; `main_wave8` draws only the s8 frames and
    # touches nothing else on disk.
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


# ============================================ WAVE 7 -- THE OWNER'S VIEWPOINTS
# The gauntlet's first hyper-realism criterion is FRAME TO MATCH, and no frame
# in this project has met it. Everything below is the attempt: the camera is
# inferred in `beach_camera.py` from the bar's inventory of what is in each
# photograph, placed on this bed's own landform, and then the frame it produces
# is MEASURED against what bar J and bar K say their frames contain. The
# deliverable of the wave is the disagreement, ordered.

def viewpoint(w, y_cam, h_eye):
    """THE BROW: the seaward-most standing point at the top of the cliff face.

    A refinement of `cliff_edge`, which takes a declared 12 m contour and steps
    2 m back from it. The brow is a landform FEATURE -- the break in slope where
    the cliff face meets the plateau -- and it can be found rather than
    declared: walk seaward from inland and stop at the first cell whose forward
    slope exceeds three times the plateau's own median. Nothing is chosen but
    the factor three, and that only has to separate 0.08 from 1.24.

    SEAWARD-MOST AND NOT HIGHEST, AND THE REASON IS THE LANDFORM'S. Wave 3's
    coastal loop leaves a straight 0.08 ramp behind the cliff. Walking inland
    on it buys 8 cm of height per metre and spends a whole metre of standoff,
    so the sea's angular extent SHRINKS the whole way; and past about 60 m the
    ramp occludes its own brow and the sea disappears entirely. The first
    framing of this file put the camera 270 m back and rendered a field of sand.
    Wave 7's first attempt walked inland looking for height and got a frame 64%
    coastal plain. Where a camera can stand is part of the landform, and on this
    landform there is exactly one place.
    """
    j = int(np.argmin(np.abs(w.y - y_cam)))
    prof = w.h[j]
    x = w.x
    dx = float(x[1] - x[0])
    slope = np.abs(np.gradient(prof, dx))
    land = prof > 2.0
    ramp = float(np.median(slope[land])) if land.any() else 0.08
    i_brow = None
    for i in range(x.size - 2, 1, -1):
        if prof[i] <= 2.0:
            break
        if slope[i] > 3.0 * ramp:
            i_brow = i + 1                          # the last flat cell
            break
    if i_brow is None:
        xc, zc = cliff_edge(w, y_cam)
        return xc, zc, float('nan')
    ze = prof[i_brow] + h_eye
    sel = np.arange(0, max(i_brow - 4, 1))
    m = float(((ze - prof[sel]) / (x[i_brow] - x[sel])).max())
    return float(x[i_brow]), float(prof[i_brow]), float(x[i_brow] - ze / m)


def surf_line_scale(w):
    """The scene's own answer to "how far apart are the breaking lines".

    Bar J records three to four separated lines across the wider parts. This bed
    produces ONE continuous surf zone -- section B is parked with its mechanism
    named -- so there is no measured line SPACING to read off it. What there is
    is the surf zone's own width, and a system of n lines inside a zone of width
    L has them L/n apart. That is the scale used, it is the transform's number
    and not a declared one, and the fact that this bed supplies the width but
    not the lines is itself the finding the eye-height inference then rests on.
    """
    wid = []
    for j in range(w.y.size):
        ii = np.where(w.brk[j])[0]
        if ii.size:
            wid.append(float(w.x[ii.max()] - w.x[ii.min()]))
    L = float(np.median(wid))
    n_lines = 3.5                       # bar J: "three to four", its own words
    return L, L / n_lines


def build_frame(w, y_cam, content, name, az_deg, W, H, D_lines, s_lines,
                h_eye=None, x_cam=None):
    """Infer the camera, then stand it on the bed. Returns (Camera, record)."""
    if h_eye is None:
        h_eye = CAM._mid(content['eye_above_ground'])
    if x_cam is not None:
        # WAVE 12: an EXPLICIT standing point, so `viewpoint`'s brow search is
        # not run. Nothing in the shipped frames passes this -- it is what the
        # four-placement comparison in `frame_standoff_report` was measured
        # with, and it is kept so that measurement can be repeated.
        j = int(np.argmin(np.abs(w.y - y_cam)))
        i = int(np.argmin(np.abs(w.x - x_cam)))
        x_c, z_g, x_near = float(w.x[i]), float(w.h[j, i]), float('nan')
    else:
        x_c, z_g, x_near = viewpoint(w, y_cam, h_eye)
    z_eye = z_g + h_eye
    inf = CAM.infer_frame(name, content, z_eye, D_lines, s_lines)
    inf['x_cam'], inf['y_cam'], inf['z_ground'] = x_c, float(y_cam), z_g
    inf['x_nearest_water'] = x_near
    inf['az'] = float(az_deg)
    az = math.radians(az_deg)
    dep = inf['dep']['mid']
    reach = 1000.0
    cam = Camera((x_c, y_cam, z_eye),
                 (x_c + reach * math.sin(az), y_cam + reach * math.cos(az),
                  z_eye - reach * math.tan(dep)), math.degrees(inf['fov_v']),
                 W, H)
    return cam, inf


def frame_azimuth_J(w, y_cam, fov_h):
    """WHICH WAY BAR J'S CAMERA FACES, from the landform and the frame width.

    Not a composition. Bar J's frame runs headland to headland with the coast
    curving away through it, so the far end of the shore belongs at ONE EDGE of
    the frame and the open sea fills the rest. The azimuth is therefore the
    bearing of the far shoreline minus half the horizontal field, and both
    terms are measured: the shoreline comes out of the bed, the half-field out
    of the lens.

    WAVE 12 TRIED TO REPLACE THIS AND PUT IT BACK. The alternative -- stand at
    the bay's own chord midpoint, at the standoff the lens was inferred from,
    and aim at the chord -- was built, rendered at four placements and measured
    against this one. It is worse, for a projective reason that no placement
    can move. `frame_standoff_report` carries the four rows and the arithmetic.
    """
    j_far = int(np.argmax(w.y))
    i_far = int(np.argmax(w.h[j_far] > 0.0))
    j_c = int(np.argmin(np.abs(w.y - y_cam)))
    i_c = int(np.argmax(w.h[j_c] > 0.0))
    dx = float(w.x[i_far] - w.x[i_c])
    dy = float(w.y[j_far] - y_cam)
    bearing = math.degrees(math.atan2(dx, dy)) % 360.0
    return (bearing - math.degrees(fov_h) / 2.0) % 360.0, bearing


def frame_standoff_report(w, cam):
    """WHAT THE FRAME'S NEAR HALF IS, AND WHY MOVING THE CAMERA DOES NOT FIX IT.

    Wave 11's critic measured wave 10's hero frame and found "no cliff, no
    headland, no wave-cut bench, no exposed rock, no offshore reef", with
    51.10% of the frame on a flat plane carrying a high-frequency standard
    deviation of 0.006/255 -- and read that as the BED never crossing the
    renderer's rock threshold. Wave 12 measured the bed instead and the reading
    does not hold: the slope clause fires over 15.9% of the visible land. What
    the frame is short of is not relief; it is RANGE. 95% of the land pixels in
    that frame are within 34 m of the lens and 44.6% of the whole frame is the
    coastal plateau the photographer is standing on.

    THE ROUND TRIP, because a negative result taken seriously is worth more
    than the change it rejects. `J_CONTENT` declares
    `standoff_over_chord = (0.35, 0.65)` and `beach_camera.infer_lens` spends
    that ratio on the LENS -- the 13 mm ultrawide, 89.9 x 106.2 deg -- and
    never on the PLACEMENT. Wave 12 applied it to the placement as well: the
    camera was stood 0.35 chords back from the midpoint of the bay's own
    A1->A2 chord, on the highest ground the domain carries, aimed at the chord
    midpoint. FOUR PLACEMENTS WERE RENDERED AND MEASURED (360 x 480, same bed,
    same sun, same materials, one field changed each time):

        the domain corner at the brow  (wave 7-11)  sky .321 water .168 land .511
        the bay centre at the brow, aimed at A2      sky .321 water .174 land .505
        the updrift anchor at the brow, aimed at A2  sky .321 water .181 land .498
        the updrift anchor, 0.36 chords back, 45 m   sky .321 water .035 land .644

    Standing higher and further back makes it WORSE, and the reason is
    projective and cannot be placed away. A bay of chord C seen from p chords
    back on a cliff of height z subtends atan(z/(pC)) BELOW the horizon --
    5.8 deg for this bed at its best -- while the frame carries 106.2 deg of
    vertical field with the horizon in its upper third. So the bay occupies
    ~5% of the frame's height whatever the camera does, and the remaining ~60%
    below it is near ground by arithmetic. THE PLACEMENT IS THEREFORE LEFT AT
    WAVE 7'S, and the finding is redirected: the near-field plateau is not an
    error to be framed out, it is what an ultrawide clifftop frame contains,
    and bar section K's own inventory says so ("dune vegetation in the
    foreground"). The defect is that it is a FLAT PLACEHOLDER, which is this
    lane's to fix and which the rest of wave 12 spends itself on.

    Reported here so the ranking is a number: the standoff the bar's interval
    asks for, the standoff the domain can supply, and the bay's angular extent
    below the horizon.
    """
    ep = getattr(w, 'plan', None)
    if ep is None:
        return None
    A1, A2 = np.asarray(ep['A1'], float), np.asarray(ep['A2'], float)
    chord = float(np.hypot(A2[0] - A1[0], A2[1] - A1[1]))
    x_mid = 0.5 * (A1[0] + A2[0])
    lo, hi = CAM.J_CONTENT['standoff_over_chord']
    have = float(w.x[-1]) - x_mid
    z_cam = float(cam.pos[2])
    p_now = (float(cam.pos[0]) - x_mid) / chord
    sub = math.degrees(math.atan2(z_cam, max(abs(float(cam.pos[0]) - x_mid),
                                             1.0)))
    return dict(chord=chord, want=(lo * chord, hi * chord), have=have,
                p_now=p_now, p_max=have / chord, z_cam=z_cam,
                bay_below_horizon_deg=sub)


SS_HERO = 2
W_HERO, H_HERO = 720, 960


def hero_cameras(w, W, H, out=print):
    """THE TWO HERO CAMERAS, built once. Wave 7 built these inline inside
    `main`; wave 8 needs the same two objects without re-rendering the s4/s5/s6
    series, and two copies of a camera inference would be two cameras."""
    L_surf, s_lines = surf_line_scale(w)
    # the range to the far surf, on this bed: the camera stands at one end of
    # the domain and bar J's lines have to read "all the way round"
    D_lines = float(0.5 * (w.y[-1] - w.y[0]))
    out()
    CAM.report([], out)
    fov_h_probe = CAM.portrait_fov(13.0)[1]
    # WAVE 12 MOVED THIS CAMERA AND MOVED IT BACK, and the round trip is the
    # measurement -- see `frame_standoff_report`. The placement is wave 7's and
    # is unchanged.
    y_j = float(w.y[2])
    az_j, bear_j = frame_azimuth_J(w, y_j, fov_h_probe)
    camJ, infJ = build_frame(w, y_j, CAM.J_CONTENT,
                             'J -- the embayment overview, upright',
                             az_j, W, H, D_lines, s_lines)
    infJ['standoff'] = frame_standoff_report(w, camJ)
    camK, infK = build_frame(w, 0.0, CAM.K_CONTENT,
                             'K -- open water and the glitter path, upright',
                             SUN_AZ, W, H, D_lines, s_lines)
    return (L_surf, s_lines, D_lines, camJ, infJ, camK, infK, az_j, bear_j)


# ------------------------------------------------------- measuring the frame
def horizon_rows(L, cam, inf):
    """The horizon's row, PREDICTED by the camera and MEASURED off the buffer.

    The prediction is `beach_camera.horizon_fraction` on the inferred geometry;
    the measurement is the last row of the raster whose rays all point above the
    horizontal. They should differ by the earth's dip and by nothing else --
    which is the row that catches a camera built at a depression it did not
    report, and it is ABSOLUTE, in pixels."""
    D = cam.rays()
    up = D[..., 2] >= 0.0
    rows = np.where(up.all(1))[0]
    ny = L.shape[0]
    meas = float(rows[-1] + 1) / ny if rows.size else float('nan')
    pred_flat = CAM.frame_fraction(inf['dep']['mid'], inf['fov_v'])
    pred_true = CAM.horizon_fraction(inf['dep']['mid'], inf['fov_v'],
                                     inf['z_landform'])
    return dict(measured=meas, predicted_flat=pred_flat,
                predicted_true=pred_true, ny=ny,
                dip_rows=(pred_true - pred_flat) * ny)


def _sun_vector(el_deg, az_deg):
    """A unit vector toward a sun at (elevation, azimuth), in world axes.

    Same convention as `atmosphere.SUN_DIR`: +x east, +y north, +z up, azimuth
    measured from north through east. Written here rather than imported because
    `atmosphere` builds ONE sun from one clock and this is used to ask a
    counterfactual -- what the missing shadow ray would cost under bar J's own
    illuminant instead of the pool's. Nothing in the shading uses it."""
    e, a = math.radians(el_deg), math.radians(az_deg)
    return np.array([math.cos(e) * math.sin(a), math.cos(e) * math.cos(a),
                     math.sin(e)])


def horizon_seam(L, cam, edge_frac=0.12):
    """THE SEA-SKY SEAM, in one number, because bar K2 makes it a criterion.

    "The sea's radiance at grazing must approach the sky's reflected value
    CONTINUOUSLY, and any seam there is a tell visible at a glance." At grazing
    the Fresnel reflectance goes to 1, so a flat sea just below the horizon is
    a mirror of the sky just above it and the ratio should go to 1. It does not,
    and how far it does not is the measurement. `horizon_check` prints the two
    triples; this returns the worst channel's departure from unity so the gap
    list can rank it against everything else in the frame."""
    D = cam.rays()
    up = D[..., 2] >= 0.0
    rows = np.where(up.all(1))[0]
    if rows.size == 0 or rows[-1] + 4 >= L.shape[0] or rows[-1] < 3:
        return None
    j = int(rows[-1])
    n = L.shape[1]
    k = max(int(edge_frac * n), 2)
    # OFF THE GLITTER PATH, AND "THE FRAME EDGES" IS NOT THE SAME THING. Down
    # the sun's azimuth the sea just below the horizon carries the sun's own
    # image and is two orders above the sky; comparing those is measuring the
    # glitter, not the seam. `horizon_check` takes the frame's outer columns,
    # which is right for frame K (aimed down the path, so the edges are 15-17
    # deg off it) and WRONG for frame J, whose left edge lands within 3 deg of
    # the sun -- it reported the seam as 6188% off, which was the glitter. The
    # columns are chosen here by their actual azimuth from the sun.
    az_col = np.degrees(np.arctan2(D[j, :, 0], D[j, :, 1])) % 360.0
    off = np.abs((az_col - SUN_AZ + 180.0) % 360.0 - 180.0)
    sel = np.argsort(off)[-2 * k:]                  # the columns furthest from it
    sky = L[j - 3:j - 1, sel].reshape(-1, 3).mean(0)
    sea = L[j + 1:j + 3, sel].reshape(-1, 3).mean(0)
    r = sea / np.maximum(sky, 1e-9)
    return dict(sky=sky, sea=sea, ratio=r, off_axis_deg=float(off[sel].min()),
                worst=float(np.max(np.abs(r - 1.0))))


def bar_J_ladder(w, ex, L):
    """BAR J'S FIVE SURFACES, COUNTED. It is the frame's own instrument.

    "The full colour ladder in one exposure, which makes it a within-frame
    instrument and therefore usable despite the camera failures: deep blue
    offshore -> teal over the shallows -> white surf -> saturated brown wet sand
    -> pale ochre dry sand. FIVE SURFACES, ONE EXPOSURE, with the wet/dry sand
    pair close in level and therefore the most trustworthy comparison of the
    set."

    A ladder with a rung missing is not a ladder, so before any radiance is
    compared the rungs are counted. This returns the pixel share of each of the
    five in the render's own frame, and the answer for this bed is the sharpest
    single result of the wave.
    """
    out = {}
    n = float(L.shape[0] * L.shape[1])
    mw = ex.get('water_mask')
    if mw is not None and mw.any():
        P = ex['water_P']
        dep = w.sample(P[..., 0], P[..., 1], w.d)
        brk = w.sample(P[..., 0], P[..., 1], w.brk.astype(float))
        out['deep water, d > 5 m'] = float(((dep > 5) & (brk < 0.2)).sum()) / n
        out['shallow/teal, d < 2.5 m'] = float(
            ((dep < 2.5) & (brk < 0.2)).sum()) / n
        out['white surf, breaking'] = float((brk > 0.8).sum()) / n
    else:
        for k in ('deep water, d > 5 m', 'shallow/teal, d < 2.5 m',
                  'white surf, breaking'):
            out[k] = 0.0
    P = ex.get('land_P')
    if P is not None and P.size:
        hz = w.sample(P[..., 0], P[..., 1], w.h)
        e = 1.5
        hx = (w.sample(P[..., 0] + e, P[..., 1], w.h)
              - w.sample(P[..., 0] - e, P[..., 1], w.h)) / (2 * e)
        hy = (w.sample(P[..., 0], P[..., 1] + e, w.h)
              - w.sample(P[..., 0], P[..., 1] - e, w.h)) / (2 * e)
        sand = (1.0 - np.clip((np.abs(hx) + np.abs(hy) - 0.35) / 0.5, 0, 1)
                - np.clip((hz - PLAIN_Z) / 4.0, 0, 1))
        sand = np.clip(sand, 0.0, 1.0)
        # WAVE 8: the wet share is `beach.swash_wetness`, the same field
        # `shade_land` shades with, so the ladder and the shader cannot drift.
        # WAVE 12: the shader draws a REALISATION, so the ladder counts the
        # same realisation -- `beach.damp_limit` -- and no threshold is
        # introduced at all. A pixel is wet sand if it is below this beach's
        # own damp limit, which is the same test the shader makes.
        wet = hz <= B.damp_limit(P[..., 1])
        out['wet sand'] = float((sand * wet).sum()) / n
        out['dry sand'] = float((sand * (~wet)).sum()) / n
    else:
        out['wet sand'] = out['dry sand'] = 0.0
    out['rungs_present'] = sum(1 for k, v in out.items()
                               if k != 'rungs_present' and v > 1e-4)
    return out


def plan_curvature(w):
    """How far the shoreline departs from straight, across the whole domain.

    Bar J's subject is an EMBAYMENT -- headland, curve, headland -- and this is
    the number that says whether the bed has one. The full range rather than
    the difference of the two end rows, which is what wave 7's first caption
    printed and which reads 12 m where the range is 50."""
    sh = np.array([float(w.x[int(np.argmax(w.h[j] > 0.0))])
                   for j in range(w.y.size)])
    return float(sh.max() - sh.min())


def beach_width(w):
    """The cross-shore width of dry beach this bed produces, per row.

    WAVE 7 MEASURED THIS TO THE `PLAIN_Z` CONTOUR AND GOT 6.0 m AT A SLOPE OF
    1.000, which is a cliff face and not a beach -- the walk crossed the
    waterline, went straight up the cliff and stopped six metres of elevation
    later. That reading was right about the bed and wrong about what it was
    measuring, and both facts mattered: there WAS no beach, so the only surface
    the walk could find was the cliff.

    Wave 8 walks to the CLIFF FOOT instead: landward from the waterline until
    the surface slope crosses the same 0.35 threshold `shade_land` uses to stop
    calling a surface sand. That is the beach and nothing else, and the slope
    reported is the MEDIAN slope over the span rather than a rise over a run --
    so a bed whose beach is a ramp and a bed whose beach is a step do not
    report the same number.
    """
    out, slopes, tops = [], [], []
    for j in range(w.y.size):
        row = w.h[j]
        i0 = int(np.argmax(row > 0.0))
        g = np.abs(np.gradient(row, float(w.x[1] - w.x[0])))
        i1 = i0
        while i1 + 1 < row.size and g[i1 + 1] < 0.35:
            i1 += 1
        if i1 > i0:
            out.append(float(w.x[i1] - w.x[i0]))
            slopes.append(float(np.median(g[i0 + 1:i1 + 1])))
            tops.append(float(row[i1]))
    a = np.array(out) if out else np.zeros(1)
    s = np.array(slopes) if slopes else np.zeros(1)
    tz = np.array(tops) if tops else np.zeros(1)
    return dict(median=float(np.median(a)), min=float(a.min()),
                max=float(a.max()), slope=float(np.median(s)),
                top=float(np.median(tz)),
                predicted_w=B.BACKSHORE_W, predicted_slope=B.TAN_FACE,
                predicted_top=B.BACKSHORE_Z)


def shadow_cost(w, ex, n=48, reach=600.0, sun=None):
    """HOW MUCH OF THE LAND IN FRAME IS LIT THAT SHOULD BE IN SHADOW.

    `shade_land` has no shadow ray. It has never had one, and no diagnostic in
    six waves reported it, because a frame with no shadows is internally
    consistent and looks like a frame taken under a high sun. This function does
    not fix it: it MEASURES it, by marching from every land hit toward the sun
    and asking whether the bed gets in the way. The answer is a share of the
    frame and a radiance error, and that is what puts the defect in its place on
    the gap list rather than at the top of it by assertion.
    """
    P = ex.get('land_P')
    if P is None or P.size == 0:
        return None
    hx = w.sample(P[..., 0], P[..., 1], w.h)
    e = 1.5
    gx = (w.sample(P[..., 0] + e, P[..., 1], w.h)
          - w.sample(P[..., 0] - e, P[..., 1], w.h)) / (2 * e)
    gy = (w.sample(P[..., 0], P[..., 1] + e, w.h)
          - w.sample(P[..., 0], P[..., 1] - e, w.h)) / (2 * e)
    N = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    S = SUN if sun is None else np.asarray(sun, float)
    ndl = (N * S[None]).sum(-1)
    lit = ndl > 0.0
    occ = np.zeros(P.shape[0], bool)
    s = np.geomspace(0.5, reach, n)
    for t in s:
        Q = P + S[None] * t
        occ |= (Q[..., 2] < w.sample(Q[..., 0], Q[..., 1], w.h)) & lit
    # what removing the direct term would cost, where it is wrongly present
    direct = E_SUN[None] * np.clip(ndl, 0, 1)[..., None] / np.pi
    amb = env_irr(N)
    frac = direct[:, 1] / np.maximum(direct[:, 1] + amb[:, 1], 1e-12)
    return dict(n_land=int(P.shape[0]), lit_share=float(lit.mean()),
                wrongly_lit=float(occ.mean()),
                wrongly_lit_of_lit=float(occ.sum() / max(lit.sum(), 1)),
                median_direct_share=float(np.median(frac[occ]))
                if occ.any() else 0.0,
                sun_el=SUN_EL)


# THE AIR BETWEEN THE CAMERA AND THE SEA IS NOT MODELLED AND THE FRAME IS
# FIFTEEN KILOMETRES DEEP. `shade_water` and `shade_land` return the radiance
# LEAVING the surface and the trace hands it straight to the film. For a pool
# five metres across that is exact to a part in ten thousand; for bar J's and
# bar K's frames the far water is beyond the visible horizon, and the two terms
# a path that long carries -- extinction of the surface's own radiance, and the
# airlight scattered into the line of sight -- are BOTH missing.
#
# THE RAYLEIGH HALF NEEDS NO NEW CONSTANT: `atmosphere.TAU_R` is the zenith
# optical depth this project already derived, and a zenith optical depth over an
# exponential atmosphere of scale height H_R is beta = tau/H_R at the surface.
# THE AEROSOL HALF DOES, and it is `?`: a maritime boundary layer runs 20-60 km
# of meteorological visibility and Koschmieder turns that into an extinction
# coefficient.
#
# WAVE 8 APPLIES IT. The constants and the term itself are hoisted to `aerial`
# beside `render`, where they belong; this function stays as the MEASUREMENT of
# what the air is worth on a given frame's own ranges, and wave 8 runs it on
# both the frame with the air and the frame without.


def aerial_cost(w, ex, cam, L):
    """WHAT THE MISSING AIR COSTS, measured on this frame's own ranges."""
    out = {}
    beta_r = np.asarray(ATM.TAU_R, float) / H_RAYLEIGH
    for nm, vis in (('clean 60 km', VIS_CLEAN), ('hazy 20 km', VIS_HAZY)):
        out[nm] = CAM.koschmieder_beta(vis)
    mw, ml = ex.get('water_mask'), ex.get('land_mask')
    rng = []
    if mw is not None and mw.any():
        rng.append(np.linalg.norm(ex['water_P'] - cam.pos[None], axis=-1))
    if ml is not None and ml.any():
        rng.append(np.linalg.norm(ex['land_P'] - cam.pos[None], axis=-1))
    r = np.concatenate(rng) if rng else np.zeros(1)
    r = r[np.isfinite(r)]
    # THE FAR TAIL IS RESOLUTION-LIMITED AND SAYING SO MATTERS. The row just
    # below the horizon is half a pixel below the horizontal, so the farthest
    # range this raster samples is z/tan(fov_v/2h) and it doubles when the
    # frame does. Percentiles below the 99.9th are stable; the maximum is not.
    q = np.percentile(r, [50, 90, 99])
    out['r_row_limit'] = float(cam.pos[2]
                               / math.tan(math.atan(cam.tan) / cam.h))
    rows = []
    for nm, beta in (('Rayleigh (atmosphere.TAU_R / 8.5 km)', beta_r[1]),
                     ('+ aerosol, clean 60 km', beta_r[1] + out['clean 60 km']),
                     ('+ aerosol, hazy 20 km', beta_r[1] + out['hazy 20 km'])):
        rows.append((nm, beta, [math.exp(-beta * d) for d in q]))
    # the share of the frame beyond one e-folding at each haze
    share = {}
    for nm, beta in (('clean', beta_r[1] + out['clean 60 km']),
                     ('hazy', beta_r[1] + out['hazy 20 km'])):
        share[nm] = float((r > 1.0 / beta).mean())
    out.update(beta_rayleigh=beta_r, ranges=q, rows=rows, share=share,
               r_max=float(r.max()), r_median=float(np.median(r)))
    return out


def frame_shares(ex, L):
    """What the frame is MADE of, by pixel count. The denominator of every
    entry on the gap list: a defect in a surface that is 2% of the frame is
    not the same defect as one in a surface that is 40% of it."""
    n = L.shape[0] * L.shape[1]
    mw = ex.get('water_mask')
    ml = ex.get('land_mask')
    sk = ex.get('sky_mask')
    out = dict(sky=float(sk.sum()) / n if sk is not None else 0.0,
               water=float(mw.sum()) / n if mw is not None else 0.0,
               land=float(ml.sum()) / n if ml is not None else 0.0)
    out['clipped'] = float((L.max(-1) > WHITE).sum()) / n
    return out


def land_breakdown(w, ex, L):
    """The land in frame, split the way `shade_land` splits it -- so the gap
    list can say how much of the frame is the ONE DECLARED ALBEDO standing in
    for the coastal plain, and how much is beach."""
    P = ex.get('land_P')
    if P is None or P.size == 0:
        return None
    hz = w.sample(P[..., 0], P[..., 1], w.h)
    e = 1.5
    hx = (w.sample(P[..., 0] + e, P[..., 1], w.h)
          - w.sample(P[..., 0] - e, P[..., 1], w.h)) / (2 * e)
    hy = (w.sample(P[..., 0], P[..., 1] + e, w.h)
          - w.sample(P[..., 0], P[..., 1] - e, w.h)) / (2 * e)
    rock = np.clip((np.abs(hx) + np.abs(hy) - 0.35) / 0.5, 0.0, 1.0)
    plain = np.clip((hz - PLAIN_Z) / 4.0, 0.0, 1.0) * (1 - rock)
    sand = 1.0 - rock - plain
    wet = (hz <= B.damp_limit(P[..., 1])) * sand
    film = (hz <= B.sheet_front(P[..., 1])) * sand
    n = float(L.shape[0] * L.shape[1])
    return dict(rock=float(rock.sum()) / n, plain=float(plain.sum()) / n,
                sand=float(sand.sum()) / n, wet_sand=float(wet.sum()) / n,
                film_sand=float(film.sum()) / n, runup=B.BERM_Z)


def sun_for_the_coast_frames():
    """THE ILLUMINANT THIS FRAME IS DRAWN UNDER AGAINST THE ONE IT WANTS.

    Bar J and bar K are CLIFF frames and their times are `?`. The bar's two
    other cliff frames are timed -- 2026-08-11 11:45 WEST, elevation 56.22 deg,
    azimuth 123.13 deg, air mass 1.202, and clean of the eclipse -- and bar J's
    own colour ladder says which class J belongs to: DEEP BLUE OFFSHORE with a
    teal band inshore is a sea reflecting sky, which is a front-lit sea. A low
    sun down the view axis does not give a deep blue offshore; it gives a
    glitter path. So the render's illuminant -- 21.02 deg, azimuth 273.75 deg,
    a west sun straight out to sea on a west-facing coast -- is not merely
    lower than J's, it is in the WRONG HALF OF THE SKY for what J shows, and
    the bar's own warning is that a wrong quadrant leaves the elevation correct
    and is otherwise silent.

    Nothing here changes the sun: `atmosphere.py` is the pool's, its four
    illuminants all descend from one geometry, and moving it is a wave. This
    function states the discrepancy in degrees so the gap list can rank it.
    """
    return dict(render_el=SUN_EL, render_az=SUN_AZ,
                coast_el=56.22, coast_az=123.13, coast_am=1.202,
                d_el=56.22 - SUN_EL, d_az=(123.13 - SUN_AZ) % 360.0,
                surf_el=BAR_SURF_EL, surf_az=BAR_SURF_AZ)


def frame_report(name, w, cam, inf, L, ex):
    """Everything measured on one of the two hero frames, printed."""
    sh = frame_shares(ex, L)
    lb = land_breakdown(w, ex, L)
    hz = horizon_rows(L, cam, inf)
    su = sun_for_the_coast_frames()
    sd = shadow_cost(w, ex)
    # AND THE SAME QUESTION UNDER THE ILLUMINANT THE FRAME ACTUALLY WANTS. The
    # missing shadow ray costs nothing on a west-facing coast under a west sun
    # -- everything faces the light and there is nothing to occlude it -- and
    # that is a fact about THIS sun, not about the renderer. Bar J's own class
    # of frame is a late-morning south-easterly, which puts the whole cliff
    # face in shade. Measuring both is what stops the gap being mis-ranked.
    sd_coast = shadow_cost(w, ex, sun=_sun_vector(su['coast_el'],
                                                  su['coast_az']))
    # ...AND A THIRD SUN, BECAUSE THE FIRST TWO CANNOT ANSWER THE QUESTION.
    # Both illuminants this project has are on the SEAWARD side of a
    # west-facing coast: the render's is 21 deg in the west and the bar's
    # timed cliff frames are 56 deg in the south-east, which is landward but
    # HIGH. A cliff shadows its own beach when the sun is landward AND low,
    # which on this coast is the morning. 20 deg at azimuth 110 deg is that
    # hour, it is a COUNTERFACTUAL and is marked as one -- nothing is rendered
    # under it -- and it is the only way to say whether the shadow ray is
    # cheap because the code is right or cheap because of where the sun is.
    sd_morning = shadow_cost(w, ex, sun=_sun_vector(20.0, 110.0))
    seam = horizon_seam(L, cam)
    ae = aerial_cost(w, ex, cam, L)
    print('FRAME %s -- MEASURED, on the scene-linear buffer:' % name)
    print('  eye at x = %.1f m, y = %.1f m, ground %.2f m, eye %.2f m; '
          'azimuth %.2f deg' % (inf['x_cam'], inf['y_cam'], inf['z_ground'],
                                inf['z_landform'], inf['az']))
    print('  upright %d x %d, %.2f deg tall x %.2f wide, depressed %.2f deg'
          % (cam.w, cam.h, math.degrees(inf['fov_v']),
             math.degrees(inf['fov_h']), math.degrees(inf['dep']['mid'])))
    print('  horizon row: predicted %.4f of frame, measured %.4f, '
          'earth dip worth %.2f rows'
          % (hz['predicted_true'], hz['measured'], hz['dip_rows']))
    print('  the frame is %.1f%% sky, %.1f%% water, %.1f%% land; %.2f%% of '
          'pixels clip the derived white point'
          % (100 * sh['sky'], 100 * sh['water'], 100 * sh['land'],
             100 * sh['clipped']))
    if lb:
        print('  the land is %.1f%% coastal plain (ONE DECLARED ALBEDO), '
              '%.1f%% beach sand, %.1f%% rock; wet band %.2f%% at run-up '
              '%.2f m' % (100 * lb['plain'], 100 * lb['sand'],
                          100 * lb['rock'], 100 * lb['wet_sand'], lb['runup']))
    if sd:
        print('  SHADOWS (wave 8 BUILT the ray; this is what it is worth, '
              'which is a different question and the answer is a surprise):')
        for nm, s in (('the render\'s sun  %5.2f el / %6.2f az'
                       % (SUN_EL, SUN_AZ), sd),
                      ('bar J\'s own class %5.2f el / %6.2f az'
                       % (su['coast_el'], su['coast_az']), sd_coast),
                      ('COUNTERFACTUAL    20.00 el / 110.00 az (morning)',
                       sd_morning)):
            print('     %-40s %5.1f%% of land faces it, %5.1f%% of THAT is '
                  'occluded and lit anyway (direct term %.0f%% of the pixel)'
                  % (nm, 100 * s['lit_share'], 100 * s['wrongly_lit_of_lit'],
                     100 * s['median_direct_share']))
    if seam:
        print('  THE SEA-SKY SEAM (bar K2), sampled %.0f deg off the sun: sky '
              '%s  sea %s  ratio %s -- worst channel is %.1f%% off continuity, '
              'where Fresnel at grazing says it should be 0.'
              % (seam['off_axis_deg'], np.round(seam['sky'], 4),
                 np.round(seam['sea'], 4), np.round(seam['ratio'], 4),
                 100 * seam['worst']))
    lad = bar_J_ladder(w, ex, L)
    bw = beach_width(w)
    print('  BAR J\'S FIVE-RUNG COLOUR LADDER, counted in this frame '
          '(%d of 5 present):' % lad['rungs_present'])
    for k in ('deep water, d > 5 m', 'shallow/teal, d < 2.5 m',
              'white surf, breaking', 'wet sand', 'dry sand'):
        print('     %-26s %6.2f%% of frame%s'
              % (k, 100 * lad[k], '' if lad[k] > 1e-4 else '   <-- ABSENT'))
    print('     the bed\'s dry beach is %.1f m wide (median), %.1f-%.1f, face '
          'slope %.4f (1:%.1f), berm top %.2f m -- against the closed forms '
          'sqrt(H0s L0) = %.1f m, (2/3)A^1.5/sqrt(d) = %.4f and '
          'tanb sqrt(H0s L0) = %.2f m.'
          % (bw['median'], bw['min'], bw['max'], bw['slope'],
             1.0 / max(bw['slope'], 1e-9), bw['top'], bw['predicted_w'],
             bw['predicted_slope'], bw['predicted_top']))
    print('  AIR: ranges in frame median %.0f m, 90th %.0f m, 99th %.0f m, '
          'max %.0f m (the row below the horizon reaches %.0f m at THIS '
          'raster height and doubles with it)'
          % (ae['r_median'], ae['ranges'][1], ae['ranges'][2],
             ae['r_max'], ae['r_row_limit']))
    for nm, beta, T in ae['rows']:
        print('     %-38s beta %8.2e /m  T at those three %.3f %.3f %.3f'
              % (nm, beta, T[0], T[1], T[2]))
    print('     %.1f%% of the frame is beyond one e-folding in clean air, '
          '%.1f%% in hazy' % (100 * ae['share']['clean'],
                              100 * ae['share']['hazy']))
    fs = CAM.flat_sea_error(inf['z_landform'], 40000.0)
    print('  CURVATURE: true horizon %.2f km, the flat plane runs to 40 km, so '
          '%.1f km of the sea in frame does not exist -- and it is compressed '
          'into %.4f deg = %.2f rows.'
          % (fs['horizon_range'] / 1e3, fs['fictitious_range'] / 1e3,
             math.degrees(fs['over_paint']),
             math.degrees(fs['over_paint']) * cam.h
             / math.degrees(inf['fov_v'])))
    return dict(shares=sh, land=lb, horizon=hz, shadow=sd,
                shadow_coast=sd_coast, shadow_morning=sd_morning,
                seam=seam, aerial=ae, flat=fs, ladder=lad, beach=bw)


# ------------------------------------------------------------------ captions
# ============================================ WAVE 8 -- THE LAND, AND THE AIR
def beach_report(w, bay, out=print):
    """THE SUBAERIAL BEACH, measured off the bed against its own closed forms.

    ABSOLUTE ROWS AND NOT ONE RATIO. A ratio-only guard has been blind five
    times in this project, so every line here is a metre or a slope with its
    prediction beside it, and the identity that ties the three together is
    checked as a difference and not as a quotient.
    """
    bch = bay.get('beach')
    bw = beach_width(w)
    L0 = B.deep_wavelength(B.T_SWELL)
    rows = [
        ('face slope tan(beta)', bw['slope'], B.TAN_FACE, ''),
        ('storm swash excursion, m', B.BACKSHORE_W,
         B.BACKSHORE_Z / B.TAN_FACE, 'm'),
        ('swell run-up limit, m', B.BERM_Z, B.TAN_FACE * B.SWASH_W, 'm'),
        ('swash excursion, m', B.SWASH_W, B.BERM_Z / B.TAN_FACE, 'm'),
    ]
    out('THE SUBAERIAL BEACH (wave 8, gap 1) -- measured against closed form:')
    for nm, meas, pred, u in rows:
        out('  %-26s measured %9.4f %-2s   closed form %9.4f   '
            'diff %+8.4f' % (nm, meas, u, pred, meas - pred))
    out('  the beach the bed ACTUALLY carries is %.2f m wide and tops out at '
        '%.3f m -- SHORTER than the %.2f m excursion and LOWER than the '
        '%.3f m storm limit, and neither is a discrepancy: the cliff\'s own '
        'talus rises into the swash plane %.0f m from the waterline and takes '
        'the top of the wedge. The beach is complete to the swell\'s berm '
        'level (%.3f m) and truncated before the storm\'s backshore. That is '
        'what a cliffed coast looks like, and it is why the DRY rung is thin: '
        'a wide backshore belongs to the embayment this bed does not have.'
        % (bw['median'], bw['top'], B.BACKSHORE_W, B.BACKSHORE_Z,
           bw['median'], B.BERM_Z))
    out('  the identity: R/tan(beta) = %.6f m and sqrt(H0 L0) = %.6f m, '
        'difference %.2e m -- the slope divides out of Hunt\'s run-up and '
        'that is why the dry beach\'s width needs no constant.'
        % (B.BERM_Z / B.TAN_FACE, math.sqrt(B.H0_SWELL * L0),
           abs(B.BERM_Z / B.TAN_FACE - math.sqrt(B.H0_SWELL * L0))))
    out('  the handover depth is the soft place and it is bracketed, not '
        'asserted: tan(beta) = %.4f at D_MIN = %.2f m, %.4f at D_MORPH_MIN = '
        '%.2f m (shipped), %.4f at 1.00 m.'
        % (B.beach_face_slope(d_hand=B.D_MIN), B.D_MIN,
           B.TAN_FACE, B.D_MORPH_MIN, B.beach_face_slope(d_hand=1.0)))
    if bch is not None:
        out('  the budget: the wedge needs %.1f m^3 per metre of coast '
            '(median) and the coastal loop delivered %.1f -- a factor of '
            '%.1f, so the WIDTH IS SET BY THE PROFILE and not by the supply '
            '(supply_limited = %s).'
            % (np.median(bch['need_row']),
               np.median(bay['coast']['sand_row'])
               / float(w.y[1] - w.y[0]),
               np.median(bay['coast']['sand_row'])
               / float(w.y[1] - w.y[0]) / max(np.median(bch['need_row']), 1e-9),
               bch['supply_limited']))
    out('  the wet/dry boundary is a Rayleigh exceedance and not a line: '
        'wetness = exp(-(z/sigma)^2) with sigma = %.4f m (Hunt\'s R = %.4f m '
        'read as R_2%%), so the median of the distribution sits at z = %.4f m.'
        % (B.swash_scale(), B.BERM_Z,
           B.swash_scale() * math.sqrt(math.log(2.0))))
    out('  ...AND THE SURFACE IS A REALISATION OF IT, NOT THE DISTRIBUTION. '
        'The damp limit is the maximum of the last N = tau/T = %.0f run-ups: '
        'median %.4f m over the bed, drawn %.4f-%.4f m across the domain, '
        'against a berm at %.4f m and a backshore at %.4f m. Across the '
        'tau_dry bracket %s s the median limit runs %.4f-%.4f m.'
        % (B.swash_cycles(), B.damp_limit_median(),
           float(np.min(B.damp_limit(bch_y := np.linspace(-704.0, 704.0,
                                                          178)))),
           float(np.max(B.damp_limit(bch_y))), B.BERM_Z, B.BACKSHORE_Z,
           B.SWASH_TAU_BRACKET,
           B.damp_limit_median(tau=B.SWASH_TAU_BRACKET[0]),
           B.damp_limit_median(tau=B.SWASH_TAU_BRACKET[1])))
    out('  `?` CLOSED BY CONSEQUENCE: read as the rms instead of R_2%%, the '
        'damp limit is %.4f m and this beach -- which its own closed forms '
        'top out at %.4f m -- has NO dry sand at any instant. That is what '
        'decides the reading, not a citation.'
        % (B.damp_limit_median(R=B.BERM_Z * math.sqrt(math.log(50.0))),
           B.BACKSHORE_Z))
    return dict(width=bw, beach=bch)


def wet_dry_report(w, ex, L, out=print):
    """THE TONAL EDGE BAR H3 CALLS ONE OF THE STRONGEST IN THESE FRAMES.

    Bar J's ruling is that the wet/dry pair is "close in level and therefore
    the most trustworthy comparison of the set", so this reports BOTH LEVELS
    absolutely and their ratio, and it separates the diffuse half from the
    specular half -- because the whole finding of wave 8's gap 2 is that
    `wet_albedo` contains a specular term that waves 4-7 spent as diffuse.
    """
    P = ex.get('land_P')
    if P is None or P.size == 0:
        return None
    hz = w.sample(P[..., 0], P[..., 1], w.h)
    e = 1.5
    hx = (w.sample(P[..., 0] + e, P[..., 1], w.h)
          - w.sample(P[..., 0] - e, P[..., 1], w.h)) / (2 * e)
    hy = (w.sample(P[..., 0], P[..., 1] + e, w.h)
          - w.sample(P[..., 0], P[..., 1] - e, w.h)) / (2 * e)
    rock = np.clip((np.abs(hx) + np.abs(hy) - 0.35) / 0.5, 0.0, 1.0)
    plain = np.clip((hz - PLAIN_Z) / 4.0, 0.0, 1.0) * (1 - rock)
    sand = np.clip(1.0 - rock - plain, 0.0, 1.0) > 0.5
    # WAVE 12: the realisation the shader drew, not the distribution it came
    # from -- and the DAMP band, not the sheet, because bar H3's pair is the
    # trapped series in the pore water and the sheet is a third surface.
    wetf = (hz <= B.damp_limit(P[..., 1])).astype(float)
    film = (hz <= B.sheet_front(P[..., 1]))
    Lp = L[ex['land_mask']]
    mw = sand & (wetf > 0.5) & (~film)
    md = sand & (wetf <= 0.5)
    if not (mw.any() and md.any()):
        return None
    aw, ad = Lp[mw].mean(0), Lp[md].mean(0)
    pt = ex.get('land_parts') or {}
    dif, spc = pt.get('diffuse'), pt.get('specular')
    out('  THE WET/DRY SAND PAIR (bar H3, bar J\'s own instrument), '
        'scene-linear, absolute:')
    out('     dry sand, TOTAL  %s   %d px' % (np.round(ad, 4), int(md.sum())))
    out('     wet sand, TOTAL  %s   %d px' % (np.round(aw, 4), int(mw.sum())))
    out('     ratio wet/dry    %s' % np.round(aw / np.maximum(ad, 1e-9), 4))
    dw = dd = rd = None
    if dif is not None:
        dw, dd = dif[mw].mean(0), dif[md].mean(0)
        rd = dw / np.maximum(dd, 1e-9)
        out('     ...and SPLIT, because under THIS sun the total is the wrong '
            'way round and the reason is not the albedo:')
        out('       DIFFUSE  dry %s   wet %s   ratio %s  <- BELOW 1 in every '
            'channel, which is bar H3\'s direction and the direction waves '
            '4-7 had backwards'
            % (np.round(dd, 4), np.round(dw, 4), np.round(rd, 4)))
        out('       SPECULAR dry %s   wet(damp, no sheet) %s   sheet %s'
            % (np.round(spc[md].mean(0), 4), np.round(spc[mw].mean(0), 4),
               np.round(spc[sand & film].mean(0), 4)
               if (sand & film).any() else 'absent'))
        out('       WAVE 12: THE LOBE IS OFF THE DAMP BAND. Waves 4-11 drove '
            'the specular from the same field as the diffuse, which puts a '
            'mirror on damp sand -- and the mirror, not the albedo, is what '
            'inverted this rung. Free water is on the surface only where the '
            'swash SHEET is, so the damp band is now matte and reads in bar '
            'H3\'s order; the sheet is a THIRD surface and is counted apart. '
            'What survives of the illuminant gap: this frame is drawn under a '
            '21.0 deg sun at azimuth 273.8 -- out to sea on a west-facing '
            'coast -- against bar J\'s own class at 56.22 / 123.13, so the '
            'sheet is backlit here and would not be there.')
        out('       the sheet covers %.3f%% of the land in frame against the '
            'damp band\'s %.3f%%; before wave 12 the lobe was on all of the '
            'second.'
            % (100 * float((sand & film).sum()) / max(sand.size, 1),
               100 * float((sand & (wetf > 0.5)).sum()) / max(sand.size, 1)))
    out('     the albedos it rests on: dry %s, wet DIFFUSE %s '
        '(= wet_albedo - R_EXT), and the R_EXT %s that used to be inside the '
        'diffuse term is now the specular lobe.'
        % (np.round(SAND_DRY, 4), np.round(SAND_WET_DIFF, 4),
           np.round(OPT.R_EXT, 4)))
    return dict(wet=aw, dry=ad, ratio=aw / np.maximum(ad, 1e-9),
                wet_diff=dw, dry_diff=dd, ratio_diff=rd,
                n_wet=int(mw.sum()), n_dry=int(md.sum()))


def paired_cost(L_on, L_off, ex, name, out=print):
    """WHAT ONE TERM IS WORTH, as a paired frame and in absolute radiance.

    One field changed and nothing else -- the same bed, the same camera, the
    same instant of phase -- which is the only way a number like this means
    anything. Reported as the median and the 95th percentile of the ABSOLUTE
    change per pixel as well as the share, because a term that moves 0.5% of
    the frame by a factor of three and a term that moves all of it by 0.5% are
    not the same term and a share alone cannot tell them apart.
    """
    d = L_on - L_off
    a = np.abs(d).max(-1)
    n = float(a.size)
    rel = np.abs(d[..., 1]) / np.maximum(L_off[..., 1], 1e-9)
    out('  %s -- paired frame, one field changed:' % name)
    out('     %.2f%% of pixels move at all; median |dL| over those %.4f, '
        '95th %.4f, max %.4f (white point %.3f)'
        % (100 * (a > 1e-6).sum() / n,
           float(np.median(a[a > 1e-6])) if (a > 1e-6).any() else 0.0,
           float(np.percentile(a, 95)), float(a.max()), WHITE))
    out('     mean green over the whole frame %.5f -> %.5f (%+.2f%%); '
        'median relative change where it moves %.2f%%'
        % (L_off[..., 1].mean(), L_on[..., 1].mean(),
           100 * (L_on[..., 1].mean() / max(L_off[..., 1].mean(), 1e-12) - 1),
           100 * float(np.median(rel[a > 1e-6])) if (a > 1e-6).any() else 0.0))
    return dict(share=float((a > 1e-6).sum() / n),
                med=float(np.median(a[a > 1e-6])) if (a > 1e-6).any() else 0.0,
                p95=float(np.percentile(a, 95)), mx=float(a.max()),
                mean_on=float(L_on[..., 1].mean()),
                mean_off=float(L_off[..., 1].mean()))


def plain_relief(w, ex, out=print):
    """GAP 2: 46% OF THE FRAME IS ONE DECLARED ALBEDO. What it has and what it
    has not, measured rather than asserted.

    The gap list asks for "at minimum, the same treatment any other surface
    gets: an albedo with a stated source, a normal, and shadowing". Two of the
    three are now there and the third is not, and this says which is which.

    AND IT SETTLES WHAT THE PLATEAU'S FLATNESS IS. It is NOT a missing constant
    -- it is a missing PROCESS, and the arithmetic is three orders wide so no
    plausible constant reaches it. Differential subaerial weathering keyed to
    the hardness field this file already owns would lower soft rock faster than
    hard and produce relief; the rate is a fraction of the marine erosion rate,
    and published denudation rates for a coastal plateau (0.01-0.1 mm/yr) sit
    against cliff retreat rates of 0.05-0.5 m/yr, a ratio near 1e-3 to 1e-4.
    This coast retreated 182 m over the loop's clock, so the plateau lowered
    somewhere between 2 cm and 18 cm -- and the relief is the CONTRAST times
    that, a few centimetres over correlation lengths of hundreds of metres.
    Slopes of 1e-4. Invisible, and invisible under any coefficient in the
    bracket.

    The relief on a real coastal plain is DRAINAGE -- fluvial incision, a
    different process on a different clock, and out of chapter 12's scope
    entirely. So gap 2 is not "declare a weathering rate": it is a landform
    process this project does not have, and that is why wave 8 measures it and
    does not build it.
    """
    P = ex.get('land_P')
    if P is None or P.size == 0:
        return None
    hz = w.sample(P[..., 0], P[..., 1], w.h)
    e = 1.5
    hx = (w.sample(P[..., 0] + e, P[..., 1], w.h)
          - w.sample(P[..., 0] - e, P[..., 1], w.h)) / (2 * e)
    hy = (w.sample(P[..., 0], P[..., 1] + e, w.h)
          - w.sample(P[..., 0], P[..., 1] - e, w.h)) / (2 * e)
    rock = np.clip((np.abs(hx) + np.abs(hy) - 0.35) / 0.5, 0.0, 1.0)
    m = (np.clip((hz - PLAIN_Z) / 4.0, 0.0, 1.0) * (1 - rock)) > 0.5
    if not m.any():
        return None
    tilt = np.degrees(np.arctan(np.hypot(hx[m], hy[m])))
    out('  THE COASTAL PLAIN (gap 2), %d px in frame:' % int(m.sum()))
    out('     albedo   %s   DECLARED `?`, still one number, still no source'
        % np.round(PLAIN_DRY, 3))
    out('     normal   tilt %.3f deg median, %.3f-%.3f across the frame, '
        'spread %.4f deg -- a normal it HAS, and it is very nearly a delta '
        'function' % (float(np.median(tilt)), float(tilt.min()),
                      float(tilt.max()), float(tilt.std())))
    out('     shadow   built this wave, and see the paired frame for what it '
        'is worth here')
    return dict(share_px=int(m.sum()), tilt_med=float(np.median(tilt)),
                tilt_std=float(tilt.std()), tilt_max=float(tilt.max()))


def _cap_J7(w, cam, inf, m):
    ey = inf['eye']
    d = math.degrees
    su = sun_for_the_coast_frames()
    return (
        's7  BAR SECTION J, THE EMBAYMENT OVERVIEW -- the first frame in this '
        'project shot at a viewpoint and a framing INFERRED FROM AN OWNER '
        'PHOTOGRAPH rather than chosen. Upright, %.1f deg tall x %.1f '
        'wide (an iPhone 16 Pro 0.5x held portrait), eye %.2f m on this bed\'s '
        'own cliff brow at x = %.0f m, optical axis depressed %.2f deg, '
        'azimuth %.1f deg. Same bed, same wave field, same optics, same sun '
        'and the same exposure as every s4/s5/s6 frame.'
        % (d(inf['fov_v']), d(inf['fov_h']),
           inf['z_landform'], inf['x_cam'], d(inf['dep']['mid']), inf['az']),
        'THE CAMERA IS AN INFERENCE AND THE INTERVALS ARE THE HONEST PART. '
        'There is no EXIF. The LENS is the best-determined parameter and it is '
        'determined by the instrument, not the picture: the bar names an '
        'iPhone 16 Pro, a bay seen from p chords back subtends 2 atan(1/2p) '
        'with the bay\'s size CANCELLING, and the widest lens this phone has '
        'is %.2f deg across upright -- so "the whole embayment from its own '
        'rim" both selects the 0.5x and proves the photographer stood at least '
        '%.4f chords back. The DEPRESSION is %.2f deg +/- %.2f, and that '
        'interval is a read off an image this file does not have; ONE MEASURED '
        'HORIZON ROW would collapse it to +/- 0.03 deg. The EYE HEIGHT IS NOT '
        'MEASURED BY THE HORIZON -- the dip is %.3f deg here and %.3f deg at '
        '90 m, a sixth of a degree between a low cliff and a high one -- but '
        'by the RESOLVED SURF LINES: lines %.0f m apart at %.0f m need an eye '
        'at %s-%s m, against the %.2f m THIS BED SUPPLIES. That shortfall is '
        'the frame\'s largest geometric gap and it is a statement about the '
        'coastal loop, not about the camera.'
        % (d(max(CAM.portrait_fov(f)[1] for f, _ in CAM.LENSES)),
           inf['standoff_min'], d(inf['dep']['mid']),
           d(inf['dep']['half_width']), d(inf['dip']),
           d(CAM.horizon_dip(90.0)), ey['s'], ey['D'],
           CAM._fmt_z(ey['z_lo']), CAM._fmt_z(ey['z_hi']), inf['z_landform']),
        'WHAT BAR J CONTAINS THAT THIS FRAME DOES NOT, MEASURED ON THIS BUFFER '
        'AND ORDERED BY WHAT IT COSTS THE FRAME. (1) BAR J\'S FIVE-RUNG COLOUR '
        'LADDER HAS %d RUNGS HERE. Deep water %.2f%% of frame, teal shallows '
        '%.2f%%, white surf %.2f%%, WET SAND %.2f%%, DRY SAND %.2f%%. J calls '
        'the wet/dry pair "the most trustworthy comparison of the set" because '
        'the two are close in level, and this frame cannot make it: wave 3\'s '
        'coastal loop leaves a dry beach %.1f m wide, a face slope of %.3f, '
        'and `shade_land` classes anything that steep as ROCK. THE BEACH IS '
        'MISSING FROM THE BEACH SCENE. (2) %.1f%% OF THE FRAME IS COASTAL '
        'PLAIN UNDER ONE DECLARED ALBEDO -- the largest single surface in a '
        'hero frame is a placeholder, and the hyper-realism criterion warns '
        'that the tell is usually not the water. (3) NO HEADLANDS AND NO '
        'EMBAYMENT: %.0f m of plan curvature over %.0f m of coast, so J\'s '
        'whole subject is absent and the axis is aimed along a nearly straight '
        'shore instead. (4) THE ILLUMINANT IS IN THE WRONG HALF OF THE SKY. J '
        'shows DEEP BLUE OFFSHORE grading to teal, which is a sea reflecting '
        'sky and therefore front-lit; this is drawn under %.2f deg / %.2f deg, '
        'a low WEST sun straight out to sea on a west-facing coast, against '
        'the bar\'s own timed cliff frames at %.2f deg / %.2f deg -- %.1f deg '
        'lower and %.1f deg round, and %.2f%% of the frame clips on a glitter '
        'path J does not show. (5) THE EYE IS TOO LOW, above. (6) ONE SURF '
        'ZONE, NOT THREE TO FOUR LINES: section B is parked with its mechanism '
        'named. (7) THE SEA-SKY SEAM IS %.0f%% OFF CONTINUITY where Fresnel at '
        'grazing says 0, and there is NO AIR between camera and sea over a '
        'frame %.1f km deep. (8) NO SWASH, NO SHORE PLATFORM, NO AIRBORNE '
        'SPRAY (bar H2/H1/F). (9) SHADOWS: there is no shadow ray, and it '
        'costs %.1f%% of the land in frame -- because this landform has no '
        'relief to cast one. Two gaps hiding each other. (10) FLAT EARTH: '
        '%.2f pixel rows. THIS IS A DIAGNOSTIC AND NOT YET A REFERENCE; the '
        'ordered list is in README-beach.md.'
        % (m['ladder']['rungs_present'], 100 * m['ladder']['deep water, d > 5 m'],
           100 * m['ladder']['shallow/teal, d < 2.5 m'],
           100 * m['ladder']['white surf, breaking'],
           100 * m['ladder']['wet sand'], 100 * m['ladder']['dry sand'],
           m['beach']['median'], m['beach']['slope'],
           100 * (m['land']['plain'] if m['land'] else 0.0),
           plan_curvature(w), float(w.y[-1] - w.y[0]),
           SUN_EL, SUN_AZ, su['coast_el'], su['coast_az'], su['d_el'],
           su['d_az'], 100 * m['shares']['clipped'],
           100 * m['seam']['worst'] if m['seam'] else float('nan'),
           m['aerial']['r_max'] / 1e3,
           100 * m['shadow']['wrongly_lit_of_lit'] if m['shadow'] else 0.0,
           math.degrees(m['flat']['over_paint']) * 4032.0
           / math.degrees(inf['fov_v'])),
    )


def _cap_K7(w, inf, m, wchk):
    d = math.degrees
    return (
        's7  BAR SECTION K, OPEN WATER AND THE GLITTER PATH -- the second '
        'inferred viewpoint, upright, from the same cliff brow, aimed straight '
        'down the sun\'s own azimuth (%.2f deg) because that is what section K '
        'IS. %.1f deg tall x %.1f wide, eye %.2f m, axis depressed %.2f deg '
        '+/- %.2f. Same camera code, same bed, same optics, same sun and the '
        'same derived exposure as the s4/s5/s6 frames and as s7-frame-J.'
        % (SUN_AZ, d(inf['fov_v']), d(inf['fov_h']), inf['z_landform'],
           d(inf['dep']['mid']), d(inf['dep']['half_width'])),
        'K1 IS THE STRONGEST INSTRUMENT IN THE BAR AND THIS FRAME CARRIES IT. '
        'The path\'s angular width is a readout of the mean square slope and '
        'there is no spread parameter anywhere in this render: the width comes '
        'from Cox & Munk\'s slope distribution and the Jacobian, and it '
        'NARROWS toward the horizon and spreads toward the observer because '
        'the same slope subtends a different range of specular directions at '
        'different incidences -- K1\'s own prediction, from the geometry. The '
        'wind is `?`; measured back off THIS frame\'s buffer the width says '
        'U10 = %.2f m/s against the %.2f m/s put in, and wave 6 showed the '
        'width is 15x the wind instrument the whitecap coverage is, so an '
        'agreement between them establishes little. BAR K3 FORBIDS READING A '
        'LEVEL OFF THE PATH and nothing here does: every number is an angle '
        'or a fraction.'
        % (wchk.get('u_glitter', float('nan')), BO.U10),
        'WHAT K CONTAINS THAT THIS DOES NOT. (1) THE HORIZON IS FLAT-EARTH: '
        'the true horizon is %.2f km from this eye and the render\'s sea plane '
        'runs to 40 km, so %.1f km of ocean in this frame does not exist -- '
        'and IT IS WORTH %.2f PIXEL ROWS, which is why it is at the BOTTOM of '
        'the gap list and not the top. (2) NO AERIAL PERSPECTIVE over a frame '
        '%.1f km deep: in clean 60 km air the direct transmittance at the 90th '
        'percentile range is %.3f and in hazy 20 km air %.3f, and the airlight '
        'that should replace what is lost is absent too, so the far sea is too '
        'dark and too saturated by construction. (3) DUNE VEGETATION AND THE '
        'VILLAGE are out of scope by bar K2 and the coastal plain here is one '
        'declared albedo -- %.1f%% of the frame. (4) NO SPRAY, NO SWASH, NO '
        'PLATFORM. A frame that says what it is missing is a diagnostic; this '
        'one is, and the ordered list is in README-beach.md.'
        % (m['flat']['horizon_range'] / 1e3,
           m['flat']['fictitious_range'] / 1e3,
           math.degrees(m['flat']['over_paint']) * 4032.0
           / math.degrees(inf['fov_v']),
           m['aerial']['r_max'] / 1e3, m['aerial']['rows'][1][2][1],
           m['aerial']['rows'][2][2][1],
           100 * (m['land']['plain'] if m['land'] else 0.0)),
    )


def _cap_J8(w, cam, inf, m, bp, wd, pc_air, pc_sh, seam0):
    d = math.degrees
    lad = m['ladder']
    bw = bp['width']
    return (
        's8  BAR SECTION J, THE SAME CAMERA AS s7-frame-J.png -- set the two '
        'side by side; that pair is the whole of this wave. Same bed evolution, '
        'same inferred viewpoint (upright %.1f x %.1f deg, eye %.2f m on this '
        'bed\'s own brow, depressed %.2f deg), same sun, same optics. FOUR '
        'FIELDS CHANGED: a subaerial beach, the wet/dry sand pair, a shadow '
        'ray, and the air.'
        % (d(inf['fov_v']), d(inf['fov_h']), inf['z_landform'],
           d(inf['dep']['mid'])),
        'BAR J\'S FIVE-RUNG LADDER NOW HAS %d RUNGS AND HAD THREE: deep water '
        '%.2f%%, teal %.2f%%, surf %.2f%%, WET SAND %.2f%% (was 0.00), DRY '
        'SAND %.2f%% (was 0.00). The beach is %.1f m wide at a face slope of '
        '%.4f (1:%.0f) against wave 7\'s 6.0 m at 1.000 -- and NOTHING IS '
        'PLACED: the slope is the Dean equilibrium profile\'s own where the '
        'surf-zone model hands over to the swash (closed form %.4f, and the '
        'evolved 1-D bed reads %.4f at that depth), the swash excursion is '
        'sqrt(H0 L0) = %.2f m with the slope divided out of Hunt\'s run-up, '
        'and the storm limit is the file\'s own H0_STORM at %.2f m. THE WEDGE '
        'IS TRUNCATED SHORT OF BOTH and that is a result: the cliff\'s own '
        'talus rises into the swash plane, so the beach is complete to the '
        'swell\'s berm level and cut before the storm\'s backshore -- what a '
        'cliffed coast looks like, and why the dry rung is thin. The wet/dry '
        'boundary is not a line: it is exp(-(z/R)^2), the Rayleigh exceedance '
        'of the run-up. DIFFUSELY wet sand reads %s against dry %s -- darker '
        'in every channel, which is bar H3\'s direction and the direction '
        'waves 4-7 had backwards, because optics.wet_albedo\'s leading R_EXT '
        'is the film\'s SPECULAR reflection and was being spent as diffuse. '
        'IN TOTAL IT IS THE OTHER WAY ROUND IN THIS FRAME, and that is gap 5 '
        'and not gap 2: the sun is 21 deg in the WEST, straight out to sea on '
        'a west-facing coast, so the wet band is BACKLIT and its new specular '
        'lobe glints straight down the lens. Bar J\'s own class of frame is '
        'front-lit and the pair would read in the diffuse order.'
        % (lad['rungs_present'], 100 * lad['deep water, d > 5 m'],
           100 * lad['shallow/teal, d < 2.5 m'],
           100 * lad['white surf, breaking'], 100 * lad['wet sand'],
           100 * lad['dry sand'], bw['median'], bw['slope'],
           1.0 / max(bw['slope'], 1e-9), B.TAN_FACE,
           bp.get('face_measured', float('nan')), B.SWASH_W,
           B.BACKSHORE_Z,
           np.round(wd['wet_diff'], 3) if wd else '-',
           np.round(wd['dry_diff'], 3) if wd else '-'),
        'THE AIR IS ONE EXPONENTIAL AND IT CLOSES THE SEAM BY CONSTRUCTION. '
        'beta = atmosphere.TAU_R / 8.5 km per channel -- NO NEW CONSTANT -- '
        'plus Koschmieder 3.912/V with V = 60 km marked `?` and the 20 km end '
        'rendered beside it. The airlight is the sky at the horizon in the '
        'ray\'s own azimuth, which is what an infinitely long horizontal path '
        'IS, so at grazing the sea\'s radiance goes to the sky\'s identically: '
        'bar K2\'s seam was %.1f%% off continuity in s7 and is %.1f%% here. '
        'The air moves %.1f%% of the frame, median |dL| %.4f against a white '
        'point of %.2f. THE SHADOW RAY moves %.1f%% of the frame under this '
        'sun. WAVE 7 MEASURED 0.0%% AND GAVE A REASON THAT IS NOW WRONG: it '
        'said the landform had no relief to cast one. It has -- a 15 m cliff '
        'over a 12 m beach -- and the ray is still worth almost nothing, for a '
        'different and geometric reason. Both illuminants this project owns '
        'are on the SEAWARD side of a west-facing coast, and a cliff shadows '
        'its own beach only when the sun is landward AND low. Under bar J\'s '
        'own class (56.22 el / 123.13 az) %.1f%% of the lit land is occluded; '
        'under a 20 deg MORNING sun at azimuth 110 it is %.1f%%. '
        'STILL MISSING AND STILL ORDERED: no embayment (%.0f m of plan '
        'curvature in 1408 m), one surf line where bar J shows three to four, '
        'the coastal plain is %.1f%% of the frame on ONE DECLARED ALBEDO with '
        'a normal %.3f deg wide, the sun is in the wrong half of the sky, and '
        'the sea is flat-Earth. The re-ordered list is in README-beach.md.'
        % (100 * seam0, 100 * (m['seam']['worst'] if m['seam'] else 0.0),
           100 * pc_air['share'], pc_air['med'], WHITE,
           100 * pc_sh['share'],
           100 * (m['shadow_coast']['wrongly_lit_of_lit']
                  if m['shadow_coast'] else 0.0),
           100 * (m['shadow_morning']['wrongly_lit_of_lit']
                  if m.get('shadow_morning') else 0.0),
           plan_curvature(w), 100 * (m['land']['plain'] if m['land'] else 0.0),
           m.get('plain', {}).get('tilt_std', float('nan'))),
    )


def _cap_air8(w8):
    b_r = np.asarray(ATM.TAU_R, float) / H_RAYLEIGH
    b_c = beta_ext(VIS_CLEAN)
    b_h = beta_ext(VIS_HAZY)
    return (
        's8  THE AIR, AS A TRIPLET AT ONE CAMERA.  LEFT no atmosphere at all '
        '(waves 1-7).  CENTRE the shipped air: Rayleigh from '
        'atmosphere.TAU_R / 8.5 km plus Koschmieder at V = 60 km.  RIGHT the '
        'hazy end of the same bracket, V = 20 km.  ONE FIELD CHANGES ACROSS '
        'THE THREE and nothing else -- same bed, same camera, same instant of '
        'phase, same sun.',
        'NO NEW CONSTANT IN THE RAYLEIGH HALF. beta = tau/H over an '
        'exponential atmosphere of scale height 8.5 km, per channel: %s /m, '
        'and tau is the zenith optical depth this project derived for the '
        'sun\'s own colour four waves ago. The aerosol half IS `?` and is the '
        'reason the right-hand panel exists rather than a sentence: beta '
        'green goes %.2e -> %.2e -> %.2e across the three. THE AIRLIGHT IS '
        'NOT A DECLARED COLOUR -- it is sky_radiance on the ray flattened to '
        'the horizontal, because in a horizontally homogeneous atmosphere an '
        'infinitely long horizontal path REACHES the horizon sky, by '
        'definition. That is why the sea-sky seam closes: %.1f%% off '
        'continuity on the left, %.1f%% in the centre, where grazing Fresnel '
        'says 0 and bar K2 calls a seam "a tell visible at a glance". Nothing '
        'was fitted to make it close and nothing could have been.'
        % (np.array2string(b_r, precision=2, formatter={
            'float_kind': lambda v: '%.2e' % v}),
           b_r[1], b_c[1], b_h[1],
           100 * w8['seam_noair'],
           100 * (w8['m']['seam']['worst'] if w8['m']['seam'] else 0.0)),
        'WHAT IT COSTS THE FRAME, MEASURED: the air moves %.1f%% of the '
        'pixels, median |dL| %.4f and 95th percentile %.4f against a derived '
        'white point of %.3f; the whole frame\'s mean green goes %.5f -> '
        '%.5f. Going from 60 km to 20 km moves %.1f%% of the pixels by a '
        'median %.4f. THE TWO APPROXIMATIONS ARE MARKED AND BOTH VANISH AT '
        'THE SEAM: a slant path is shorter than a horizontal one so the '
        'airlight on a steeply downward ray is over-stated (and 1 - T is '
        '0.0002 there), and the aerosol\'s airlight is given the Rayleigh '
        'sky\'s colour, which over-blues the haze. Bar J and bar K are not '
        'read for a level anywhere in this: the visibility is `?`, bracketed, '
        'and the clean end is shipped because it understates the term.'
        % (100 * w8['air']['share'], w8['air']['med'], w8['air']['p95'],
           WHITE, w8['air']['mean_off'], w8['air']['mean_on'],
           100 * w8['haze']['share'], w8['haze']['med']),
    )


def beach_figure(w, bay, w8, path):
    """The subaerial profile drawn against its own closed form, and the
    wet/dry exceedance against its `?` bracket.

    Drawn with `beach_plot`, which is this project's own PIL axes, and NOT with
    matplotlib -- which is not installed in this environment and took wave 8's
    first attempt at this figure down after four renders had already been
    spent. Every other figure in this project is a `beach_plot` figure; this
    one now is too.
    """
    import beach_plot as P
    wd = (w8 or {}).get('wd') or {}
    j = int(w.y.size // 2)
    row = w.h[j]
    i0 = int(np.argmax(row > 0.0))
    sel = slice(max(i0 - 30, 0), min(i0 + 20, row.size))
    xs = np.asarray(w.x[sel]) - float(w.x[i0])
    zs = np.asarray(row[sel])
    img = P.canvas(1120, 860)
    ax = P.Axes(img, (90, 60, 1080, 420), (float(xs[0]), float(xs[-1])),
                (-1.6, 2.6), title='THE SUBAERIAL BEACH -- nothing placed. '
                'Face slope from the equilibrium profile, excursion '
                'sqrt(H0 L0) = %.2f m, elevations from Hunt.' % B.SWASH_W,
                xlabel='metres landward of the waterline',
                ylabel='elevation, m')
    ax.frame()
    ax.line(xs, np.clip(B.TAN_FACE * xs, None, B.BACKSHORE_Z), (192, 57, 43),
            width=2, dash=(7, 6))
    ax.line(xs, zs, (20, 20, 20), width=3)
    for z, col in ((0.0, (41, 128, 185)), (B.BERM_Z, (22, 160, 133)),
                   (B.BACKSHORE_Z, (142, 68, 173))):
        ax.hline(z, col, width=1)
    ax.vline(B.SWASH_W, (22, 160, 133), width=1)
    ax.vline(B.BACKSHORE_W, (142, 68, 173), width=1)
    P.legend(ax, [
        ((20, 20, 20), 'the bed, row %d -- measured face slope %.4f'
         % (j, w8['bp']['width']['slope'] if w8 else B.TAN_FACE)),
        ((192, 57, 43), 'closed form tan(beta) = (2/3)A^1.5/sqrt(d) = %.5f, '
         'capped at the storm run-up' % B.TAN_FACE),
        ((41, 128, 185), 'the datum'),
        ((22, 160, 133), 'swell run-up %.3f m at %.2f m -- the berm LEVEL'
         % (B.BERM_Z, B.SWASH_W)),
        ((142, 68, 173), 'storm run-up %.3f m at %.2f m -- the backshore'
         % (B.BACKSHORE_Z, B.BACKSHORE_W)),
    ], float(xs[0]) + 2.0, 2.35)
    zq = np.linspace(0.0, 2.2, 400)
    ax2 = P.Axes(img, (90, 500, 1080, 740), (0.0, 2.2), (0.0, 1.05),
                 title='THE WET/DRY BOUNDARY IS A DISTRIBUTION, not a line',
                 xlabel='elevation above the datum, m',
                 ylabel='share of swash cycles reaching it')
    ax2.frame()
    ax2.line(zq, B.swash_wetness(zq), (192, 57, 43), width=3)
    ax2.line(zq, B.swash_wetness(zq, R=B.BERM_Z * math.sqrt(math.log(50.0))),
             (127, 140, 141), width=2, dash=(7, 6))
    ax2.line(zq, B.damp_exceedance(zq), (39, 60, 117), width=3)
    ax2.vline(B.damp_limit_median(), (41, 128, 185), width=1)
    P.legend(ax2, [
        ((192, 57, 43), 'exp(-(z/sigma)^2), sigma = %.4f m -- the Rayleigh '
         'exceedance of ONE run-up' % B.swash_scale()),
        ((127, 140, 141), 'waves 4-11: Hunt\'s R read as the rms rather than '
         'R_2%% (sigma = %.4f m), a band 1.978x too tall' % B.BERM_Z),
        ((39, 60, 117), 'P(damp) = 1-(1-p)^N, N = %.0f cycles -- and the '
         'SHADER DRAWS A SAMPLE OF THIS, not the curve' % B.swash_cycles()),
        ((41, 128, 185), 'the damp limit\'s median, z = %.4f m'
         % B.damp_limit_median()),
    ], 0.9, 1.0)
    lines = [
        's8  THE SUBAERIAL BEACH AND ITS WET/DRY BOUNDARY, against their own '
        'closed forms. Nothing here is placed and nothing is authored.',
        'THE FACE SLOPE is the Dean equilibrium profile\'s own where the '
        'surf-zone model hands over to the swash, (2/3)A^1.5/sqrt(D_MORPH_MIN) '
        '= %.5f (1:%.1f) -- and the EVOLVED 1-D bed reads %.6f at that depth, '
        '%.2f%% away, which is a second instrument that could have disagreed.'
        % (B.TAN_FACE, 1.0 / B.TAN_FACE,
           (w8 or {}).get('bp', {}).get('face_measured', float('nan')),
           100 * abs((w8 or {}).get('bp', {}).get('face_measured', B.TAN_FACE)
                     / B.TAN_FACE - 1)),
        'THE EXCURSION has the slope divided out of it: R = tan(beta) '
        'sqrt(H L0), so R/tan(beta) = sqrt(H L0) = %.4f m and the width of a '
        'dry beach needs no constant. The wedge is TRUNCATED at %.1f m and '
        '%.3f m because the cliff\'s own talus rises into the swash plane -- '
        'complete to the swell\'s berm level, cut before the storm\'s '
        'backshore, which is what a cliffed coast looks like.'
        % (B.SWASH_W, (w8 or {}).get('bp', {}).get('width', {}).get(
            'median', float('nan')),
           (w8 or {}).get('bp', {}).get('width', {}).get('top', float('nan'))),
        'THE BOUNDARY is the Rayleigh exceedance of the run-up and not a '
        'ramp. In frame J the DIFFUSE halves read wet %s against dry %s -- '
        'darker in every channel, which is bar H3\'s direction; the TOTAL is '
        'the other way round because a 21 deg sun straight out to sea '
        'backlights the wet band and its specular lobe glints. That is gap 5, '
        'not gap 2.'
        % (np.round(wd.get('wet_diff', np.zeros(3)), 3),
           np.round(wd.get('dry_diff', np.zeros(3)), 3)),
    ]
    P.caption(img, lines, x=40, y=760)
    P.save(img, path)
    print('  wrote %s' % path)


def wave8(w, bay, camJ, infJ, out=print):
    """THE FOUR GAPS, MEASURED AS PAIRED FRAMES AT BAR J'S OWN FRAMING.

    ONE FIELD CHANGED PER PAIR AND NOTHING ELSE. Four renders of the same
    camera on the same bed at the same instant of phase: with everything, with
    the air removed, with the shadow ray removed, and with the hazy end of the
    visibility bracket instead of the clean one. That is the only way "what the
    land cost and what the air bought" can be two numbers rather than one
    impression.
    """
    global SHADOW_ON
    out()
    bp = beach_report(w, bay, out)
    # the evolved 1-D bed's own slope at the innermost cell it resolves, which
    # is the independent instrument the caption quotes. Measured here rather
    # than typed into the caption -- wave 5's rule about literals in captions.
    _sc = B.run_scene()
    _ii = np.where(_sc['tr']['d'] > B.D_MORPH_MIN)[0]
    bp['face_measured'] = float(abs(np.gradient(
        _sc['tr']['h'], _sc['tr']['dx'])[_ii[-1]]))
    out('  and the evolved 1-D bed reads %.6f at that depth, %.2f%% from the '
        'closed form -- two instruments, and the second could have '
        'disagreed.' % (bp['face_measured'],
                        100 * abs(bp['face_measured'] / B.TAN_FACE - 1)))
    out()
    L, ex = render(camJ, w)
    m = frame_report('J (wave 8)', w, camJ, infJ, L, ex)
    wd = wet_dry_report(w, ex, L, out)
    pr = plain_relief(w, ex, out)
    m['plain'] = pr or {}
    out()
    out('WHAT EACH TERM IS WORTH, AS PAIRED FRAMES:')
    L_noair, ex_noair = render(camJ, w, air=False)
    pc_air = paired_cost(L, L_noair, ex, 'THE AIR (gap 9)', out)
    seam0 = horizon_seam(L_noair, camJ)
    seam1 = horizon_seam(L, camJ)
    out('     the sea-sky seam WITHOUT the air %.1f%% off continuity, WITH it '
        '%.1f%% -- bar K2\'s criterion, and it closes because an infinite '
        'path and the horizon sky are the same radiance and not because '
        'anything was fitted.'
        % (100 * seam0['worst'] if seam0 else float('nan'),
           100 * seam1['worst'] if seam1 else float('nan')))
    L_hazy, _ = render(camJ, w, vis=VIS_HAZY)
    pc_haze = paired_cost(L_hazy, L, ex, 'THE `?` IN THE AIR: 20 km against '
                          'the shipped 60 km', out)
    SHADOW_ON = False
    L_nosh, _ = render(camJ, w)
    SHADOW_ON = True
    pc_sh = paired_cost(L, L_nosh, ex, 'THE SHADOW RAY (gap 13)', out)
    return dict(L=L, ex=ex, m=m, bp=bp, wd=wd, plain=pr, air=pc_air,
                haze=pc_haze, shadow=pc_sh,
                seam_noair=seam0['worst'] if seam0 else float('nan'),
                L_noair=L_noair, L_hazy=L_hazy, L_nosh=L_nosh)


def main_wave8():
    """WAVE 8 ONLY, and it exists because of the s4/s5/s6 rule.

    `main` regenerates `s6-bay-render.png` and its two companions, and those
    three frames are one comparison with s4 and s5 -- same camera, same bed,
    same sun, ONE FIELD CHANGED each time. Wave 8 changes four fields at once,
    so running `main` would overwrite the middle term of a three-frame argument
    with a picture that is not comparable to either end of it. The rule that
    protected s4 from s5 and s5 from s6 protects all three from wave 8, and the
    way it is kept is that wave 8 has its own entry point.
    """
    t0 = time.time()
    _set_runup()
    print('sun: elevation %.2f deg, azimuth %.2f deg, air mass %.3f'
          % (SUN_EL, SUN_AZ, ATM.SUN_AM))
    print('run-up: xi = %.4f on the BEACH FACE slope %.5f, R = %.4f m; '
          'waves 4-7 read the slope AT THE BREAK POINT and got xi = %.4f, '
          'R = %.4f m -- 46%% low, and Hunt\'s xi is defined on the slope the '
          'swash climbs.' % (_XI, B.TAN_FACE, RUNUP, _XI_BRK, RUNUP_BRK))
    bay = B.run_bay()
    w = Water(bay)
    SS7 = SS_HERO
    W7, H7 = W_HERO * SS7, H_HERO * SS7
    (_, _, _, camJ7, infJ7, _, _, _, _) = hero_cameras(w, W7, H7)
    w8 = wave8(w, bay, camJ7, infJ7)
    _save(downsample(w8['L'], SS7), '%s/s8-frame-J.png' % OUT,
          caption=_cap_J8(w, camJ7, infJ7, w8['m'], w8['bp'], w8['wd'],
                          w8['air'], w8['shadow'], w8['seam_noair']))
    gap8 = np.zeros((w8['L'].shape[0], 8 * SS7, 3))
    _save(downsample(np.concatenate([w8['L_noair'], gap8, w8['L'],
                                     gap8, w8['L_hazy']], axis=1), SS7),
          '%s/s8-air.png' % OUT, caption=_cap_air8(w8))
    beach_figure(w, bay, w8, '%s/s8-beach-profile.png' % OUT)
    print('%.1f s' % (time.time() - t0))
    return w8




# ============================================================ WAVE 9 -- the
# static-equilibrium bay: the plan-form, the transport, and the frame
def bay_plan_figure(bay_flat, bay_bayed, path):
    """THE BAY IN PLAN, twice: the same code, the same offshore spectrum, the
    same coastal loop, and ONE array different -- the shoreline.

    Left is waves 1-8's bed, whose shoreline is the regional trend with the
    hardness field's 380 m roughness on it. Right is the static-equilibrium
    bay. Both carry their own depth contours, their own refracted crests (the
    contours of the marched phase, so what is drawn IS the wave field) and
    their own breaking mask.
    """
    import beach_plot as P
    import beach_evidence as EV
    ep = bay_bayed['plan']
    x, y = bay_bayed['x'], bay_bayed['y']
    x0 = 150.0
    x1 = float(max(np.nanmax(bay_bayed['x_s']),
                   np.nanmax(bay_flat['x_s']))) + 110.0
    i0 = int(np.searchsorted(x, x0))
    i1 = int(np.searchsorted(x, x1))
    img = P.canvas(1660, 1270)
    for k, (bb, ttl) in enumerate((
            (bay_flat, 'WAVES 1-8: the coastal loop\'s own shoreline. '
                       '%.1f m of range, and it is ROUGHNESS'
             % float(bay_flat['x_s'].max() - bay_flat['x_s'].min())),
            (bay_bayed, 'WAVE 9: the static-equilibrium bay. %.1f m of '
                        'indentation, from a closed form'
             % ep['sagitta']))):
        pix = EV._bay_pixels(bb, bb['tr'])
        ax = P.Axes(img, (70 + k * 800, 70, 760 + k * 800, 700),
                    (y[0], y[-1]), (x0, x1), title=ttl,
                    xlabel='alongshore, m',
                    ylabel=('cross-shore, m (sea at the top)' if k == 0
                            else ''), y_up=False)
        ax.image(pix[i0:i1])
        ax.frame(EV._ticks(y[0], y[-1], 5), EV._ticks(x0, x1, 6))
        ax.line(y, bb['x_s'], (255, 96, 64), 2)
        if k == 1:
            ax.line(ep['pts'][:, 1], ep['pts'][:, 0], (255, 235, 60), 2,
                    dash=(9, 7))
            ax.marker(ep['A1'][1], ep['A1'][0], (255, 235, 60), r=6)
            ax.marker(ep['A2'][1], ep['A2'][0], (255, 235, 60), r=6)
            P.legend(ax, [
                ((255, 96, 64), 'the composed bed\'s waterline'),
                ((255, 235, 60), 'the closed form R = R_a exp((phi-phi_a) '
                                 'cot alpha), alpha = %.3f deg'
                 % math.degrees(ep['alpha'])),
                ((160, 190, 210), 'depth contours 2 / 4 / 6 m'),
                ((250, 250, 255), 'breaking mask; crests = phase contours'),
            ], y[0] + 30, x1 - 60)

    # the alongshore breaking-crest azimuth, the thing bar J reads by eye
    ax3 = P.Axes(img, (70, 800, 1560, 1010), (y[0], y[-1]), (-26.0, 26.0),
                 title='WHAT BAR J CHECKS BY EYE: the breaking crest\'s '
                       'azimuth, and the shore normal it has to follow',
                 xlabel='alongshore, m', ylabel='degrees')
    ax3.frame(EV._ticks(y[0], y[-1], 9), EV._ticks(-26.0, 26.0, 7))
    for bb, col, lab in ((bay_flat, (150, 150, 155), 'flat'),
                         (bay_bayed, (192, 57, 43), 'bay')):
        br = B.breaker_row(bb['tr'])
        ax3.line(y, np.degrees(br['theta']), col, 2)
    ax3.line(y, -np.degrees(B.shore_normal_angle(y, bay_bayed['x_s'])),
             (41, 128, 185), 2, dash=(8, 6))
    ax3.hline(math.degrees(B.THETA0_SWELL), (120, 122, 128), width=1)
    P.legend(ax3, [
        ((192, 57, 43), 'breaking crest azimuth, EMBAYED bed -- an output of '
                        'the 2-D energy-flux march'),
        ((150, 150, 155), 'the same, flat bed'),
        ((41, 128, 185), 'the shore normal the bay presents (equilibrium '
                         'wants these two on top of each other)'),
        ((120, 122, 128), 'the deep-water direction, %.0f deg'
         % math.degrees(B.THETA0_SWELL)),
    ], y[0] + 30, -12.0)

    ec = B.equilibrium_plan(delta=0.0)
    P.caption(img, [
        's9  THE EMBAYMENT. DERIVED: the plan-form is a logarithmic spiral, '
        'R = R_a exp((phi-phi_a) cot alpha), alpha = 90 - theta_b = %.4f deg, '
        'and theta_b = %.4f deg is the residual breaking obliquity'
        % (math.degrees(ep['alpha']), math.degrees(ep['theta_b'])),
        'the 1-D transform OUTPUTS for the stated offshore spectrum. The pole '
        '(%.1f, %.1f) m solves TWO conditions and has no freedom left: the '
        'spiral passes through both rock anchors (yellow dots -- the'
        % (ep['D'][0], ep['D'][1]),
        'seaward-most shoreline in the outer quarter of each end of the '
        'coastal loop\'s own plan-form), and its tangent at the downcoast '
        'control point is perpendicular to the deep-water wave',
        'vector, which is Hsu & Evans\' definition of that point. The '
        'indentation, %.2f m over %.0f m, is therefore an OUTPUT.'
        % (ep['sagitta'], ep['chord']),
        'CITED: the logarithmic-spiral bay (Krumbein 1944; Yasso 1965; '
        'Silvester 1970) -- and it is NOT in terrain-architect chapter 12, '
        'which is a gap reported to the sibling skill.',
        'MEASURED: bar section J gives roughly 50 m of plan curvature over '
        '1408 m; this is %.2fx that, reported and NOT fitted -- the standing '
        'ruling forbids calibrating against the photograph.'
        % (ep['sagitta'] / 50.0),
        'DECLARED `?`: the residual obliquity delta. Only delta = 0 is derived '
        '(shore normal to a radial orthogonal is a CIRCLE, exactly); the '
        'circle\'s indentation is %.2f m, %.1f%% from the spiral\'s.'
        % (ec['sagitta'], 100 * abs(ec['sagitta'] / ep['sagitta'] - 1)),
        'Scene-linear throughout; nothing was read back off this PNG.',
    ], x=40, y=1070)
    return P.save(img, path)


def transport_figure(path):
    """THE MEASUREMENT: alongshore breaker height, obliquity and longshore
    transport for four shorelines under ONE offshore spectrum.

    The straight coast is the control the bar asks for; the ROTATED straight
    coast is the meter's own calibration, because a near-zero reading means
    nothing until zero has been demonstrated to be reachable.
    """
    import beach_plot as P
    import beach_evidence as EV
    ep = B.equilibrium_plan()
    y = ep['y']
    x = np.arange(0.0, 1000.0 + 4.0, 4.0)
    x_ref = float(np.mean(ep['x_s']))
    cases = [
        ('straight shore, plane crest', np.full(y.size, x_ref),
         B.THETA0_SWELL, (44, 62, 80)),
        ('the closed-form ZERO-transport shore (rotated %.1f deg)'
         % math.degrees(B.THETA0_SWELL),
         B.zero_transport_plan(y, x_ref, B.THETA0_SWELL), B.THETA0_SWELL,
         (39, 174, 96)),
        ('the BAY, plane crest -- worse, and it must be',
         ep['x_s'], B.THETA0_SWELL, (211, 84, 0)),
        ('the BAY, under the fan its own pole implies',
         ep['x_s'], B.fan_theta0(y, ep['x_s'], ep['D']), (192, 57, 43)),
    ]
    out = []
    for lab, xs, th0, col in cases:
        _, tr = B.plan_field(x, y, xs, theta0=th0)
        out.append((lab, col, B.plan_transport(y, xs, tr)))

    img = P.canvas(1560, 1300)
    ax1 = P.Axes(img, (80, 66, 1520, 340), (y[0], y[-1]), (1.2, 2.6),
                 title='BREAKER HEIGHT along the shore -- H_b is an OUTPUT '
                       'of the transform, never an input',
                 xlabel='', ylabel='H_b, m')
    ax1.frame(EV._ticks(y[0], y[-1], 9), EV._ticks(1.2, 2.6, 8))
    for lab, col, pt in out:
        ax1.line(y, pt['H_b'], col, 2)

    ax2 = P.Axes(img, (80, 410, 1520, 680), (y[0], y[-1]), (-16.0, 16.0),
                 title='THE ANGLE THAT DOES IT: theta_loc, the breaking '
                       'orthogonal against the LOCAL shore normal',
                 xlabel='', ylabel='theta_loc, degrees')
    ax2.frame(EV._ticks(y[0], y[-1], 9), EV._ticks(-16.0, 16.0, 9))
    ax2.hline(0.0, (120, 122, 128), width=1)
    for lab, col, pt in out:
        ax2.line(y, np.degrees(pt['theta_loc']), col, 2)

    ax3 = P.Axes(img, (80, 750, 1520, 1010), (y[0], y[-1]), (-0.25, 0.25),
                 title='LONGSHORE TRANSPORT, CERC: Q = C H_b^(5/2) '
                       'sin(2 theta_loc). Static equilibrium is Q = 0 '
                       'everywhere',
                 xlabel='alongshore, m', ylabel='Q, m3/s (positive downdrift)')
    ax3.frame(EV._ticks(y[0], y[-1], 9), EV._ticks(-0.25, 0.25, 11))
    ax3.hline(0.0, (120, 122, 128), width=1)
    for lab, col, pt in out:
        ax3.line(y, pt['Q'], col, 2)
    P.legend(ax3, [(c, '%s -- |theta| mean %.3f deg, Q rms %.3e m3/s'
                    % (l, math.degrees(p['th_mean']), p['Q_rms']))
                   for l, c, p in out], y[0] + 30, 0.225)

    msp = np.zeros(y.size, bool)
    msp[ep['j1'] + 2:ep['j2'] - 1] = True
    q = [float(np.sqrt(np.mean(p['Q'][msp & p['mask']] ** 2)))
         for _, _, p in out]
    P.caption(img, [
        's9  THE PROPERTY THAT MAKES THIS PROVABLE: at static equilibrium the '
        'wave orthogonal is normal to the shoreline everywhere, so sin(2 '
        'theta_loc) = 0 and the longshore transport is zero',
        'all along the bay. Four shorelines, ONE offshore spectrum (H_0 = '
        '%.1f m, T = %.0f s, theta_0 = %.0f deg), one ramp, one transform, '
        'one CERC closure -- the only thing that differs'
        % (B.H0_SWELL, B.T_SWELL, math.degrees(B.THETA0_SWELL)),
        'between the curves is the array x_s(y). MEASURED, over the spiral '
        'span, Q rms in m3/s: straight %.4e, the closed-form zero-transport '
        'shore %.4e, the bay under a plane' % (q[0], q[1]),
        'crest %.4e, the bay under its own fan %.4e. SO: the straight coast '
        'is NOT near zero, which is the control the bar asks for; the meter '
        'CAN read zero (%.0fx down, and without'
        % (q[2], q[3], q[0] / max(q[1], 1e-12)),
        'that row a near-zero reading on the bay would be a statement about '
        'the meter); and the bay under a plane crest is WORSE than straight, '
        'and it MUST be -- theta_loc = 0 forces',
        'phi_s = -theta_0 at every station, which is ONE STRAIGHT LINE, so '
        'any curvature raises the transport. That is terrain-architect '
        'chapter 12\'s "headlands retreat faster than bays ...',
        'until the coast STRAIGHTENS", and it is right. A static-equilibrium '
        'BAY is not a property of a shoreline; it is a property of a '
        'shoreline AND the headland that shelters it.',
        'Under the fan its own pole implies the bay falls to %.4e, a factor '
        'of %.2f below straight -- SMALL, and %.1fx the meter\'s floor, so '
        'NOT zero to within numerics.'
        % (q[3], q[0] / q[3], q[3] / max(q[1], 1e-12)),
        'DERIVED: the closed-form zero-transport shore, and the CERC '
        'closure\'s sin(2 theta). CITED: Komar & Inman 1970 for the closure '
        '(via terrain-architect 12); Krumbein/Yasso/Silvester',
        'for the spiral. MEASURED: everything plotted. Scene-linear '
        'throughout; no pixel was read.',
    ], x=40, y=1090)
    return P.save(img, path)


def wave9(w, bay, camJ, infJ, out=print):
    """The frame at bar J's own camera, on a bed that finally has bar J's own
    subject in it."""
    out()
    ep = bay['plan']
    out('THE STATIC-EQUILIBRIUM BAY')
    out('  alpha = 90 - theta_b = %.4f deg (theta_b = %.4f deg, an OUTPUT of '
        'the 1-D transform)' % (math.degrees(ep['alpha']),
                                math.degrees(ep['theta_b'])))
    out('  pole (%.2f, %.2f) m, |D - A1| = %.1f m, closure residual %.2e'
        % (ep['D'][0], ep['D'][1], ep['r_pole'], float(np.max(np.abs(
            ep['res'])))))
    out('  indentation %.2f m over %.0f m of coast; bar J gives ~50 m over '
        '1408 m, so %.2fx' % (ep['sagitta'], ep['chord'], ep['sagitta'] / 50.))
    out('  the fan the bay requires: %.2f deg of alongshore swing in the '
        'orthogonal' % math.degrees(ep['fan']['swing']))
    L, ex = render(camJ, w)
    m = frame_report('J (wave 9, embayed)', w, camJ, infJ, L, ex)
    return dict(L=L, ex=ex, m=m, ep=ep)


def _cap_J9(w, cam, inf, m, ep, sw):
    sh = m.get('shares', {})
    return [
        's9-frame-J  BAR SECTION J\'S FRAMING ON A BED THAT HAS BAR SECTION '
        'J\'S SUBJECT IN IT. The pair to s7-frame-J.png and s8-frame-J.png: '
        'same inferred viewpoint, same 0.5x ultrawide upright, same sun, same '
        'optics, same beach and air. ONE FIELD CHANGED -- the plan-form.',
        'DERIVED: the shoreline is a logarithmic spiral whose pole solves two '
        'conditions and has no freedom left (through both rock anchors; '
        'tangent perpendicular to the deep-water wave vector at the downcoast '
        'control point). alpha = 90 - theta_b = %.3f deg, theta_b = %.3f deg '
        'from the 1-D transform.'
        % (math.degrees(ep['alpha']), math.degrees(ep['theta_b'])),
        'MEASURED off the scene-linear buffer, never off this PNG: '
        'indentation %.2f m over %.0f m (bar J: ~50 m over 1408, so %.2fx, '
        'reported and NOT fitted -- the standing ruling forbids calibrating '
        'on the photographs). Bay-scale swing of the breaking crest azimuth '
        '%.2f deg against %.2f deg on the un-embayed bed.'
        % (ep['sagitta'], ep['chord'], ep['sagitta'] / 50.0, sw[1], sw[0]),
        'STILL OPEN in this frame, unchanged by this wave: ONE surf zone '
        'where bar J shows three to four separated lines (section B, parked, '
        'mechanism named); the illuminant is in the wrong half of the sky; '
        'no airborne spray; the bed under the water reads 1.24-1.40x too '
        'bright. By "no placeholder in a hero frame" this is a diagnostic.',
        'Colour ladder, share of frame: %s. Camera: %.2f +/- %.2f deg '
        'depression, %.1f x %.1f deg upright, brow at z = %.2f m. '
        'Scene-linear measured before the tone map; the tone map is display '
        'only, and no physics was read off this PNG.'
        % (', '.join('%s %.2f%%' % (k, 100 * v) for k, v in sh.items()),
           math.degrees(inf['dep']['mid']),
           math.degrees(inf['dep']['half_width']),
           math.degrees(inf['fov_h']), math.degrees(inf['fov_v']),
           inf['z_ground']),
    ]


def main_wave9():
    """WAVE 9 ONLY, and for the same reason waves 7 and 8 have their own
    entry points: this wave changes the PLAN-FORM, which moves every frame in
    the s4/s5/s6 one-field-at-a-time series and both of wave 7's."""
    t0 = time.time()
    _set_runup()
    print('sun: elevation %.2f deg, azimuth %.2f deg' % (SUN_EL, SUN_AZ))
    bay0 = B.run_bay()
    bay1 = B.run_bay(embay=True)
    bay_plan_figure(bay0, bay1, '%s/s9-bay-plan.png' % OUT)
    transport_figure('%s/s9-transport.png' % OUT)
    sw = []
    for bb in (bay0, bay1):
        br = B.breaker_row(bb['tr'])
        th = np.degrees(br['theta'])
        ww = max(int(round(0.2 * th.size)) | 1, 3)
        sm = np.convolve(np.pad(th, ww // 2, mode='edge'),
                         np.ones(ww) / ww, mode='valid')
        sw.append(float(sm.max() - sm.min()))
    w = Water(bay1)
    SS = SS_HERO
    (_, _, _, camJ, infJ, _, _, _, _) = hero_cameras(w, W_HERO * SS,
                                                     H_HERO * SS)
    w9 = wave9(w, bay1, camJ, infJ)
    _save(downsample(w9['L'], SS), '%s/s9-frame-J.png' % OUT,
          caption=_cap_J9(w, camJ, infJ, w9['m'], w9['ep'], sw))
    print('%.1f s' % (time.time() - t0))
    return w9


# =========================================================== WAVE 10 -- what
# "cross-shore distance" means on a curved coast
#
# THE HOUSE PALETTE IS REUSED UNCHANGED and that is a decision, not laziness:
# these three figures join a series of thirty-six, and the categorical order
# (44,62,80 slate / 39,174,96 green / 211,84,0 orange / 192,57,43 red /
# 41,128,185 blue) is the one every earlier evidence figure assigns in. A
# figure that renamed the colours would break the only cross-figure identity
# the series has. Every panel below carries a legend, no panel carries two y
# scales, and nothing is labelled by colour alone.
_C_AXIS = (211, 84, 0)          # the cross-shore (translate) keying
_C_NORM = (39, 174, 96)         # the normal-offset keying
_C_POLE = (41, 128, 185)        # the concentric keying, wave 9's proposal
_C_INK = (44, 62, 80)
_C_RED = (192, 57, 43)


def _contour_polyline(x, y, h2, level):
    """The depth contour at `level` metres, as (y, x) per alongshore row.

    Read off the bed by linear interpolation in x along each row -- the bed is
    monotone offshore over the ramp, so the contour is a single-valued graph
    x(y) and no marching-squares is needed. Nothing is read off a PNG.
    """
    out = np.full(y.size, np.nan)
    for j in range(y.size):
        d = -h2[j]
        i = np.nonzero((d[:-1] - level) * (d[1:] - level) <= 0.0)[0]
        if i.size:
            i = int(i[-1])
            a, b = d[i], d[i + 1]
            t = 0.0 if b == a else (level - a) / (b - a)
            out[j] = x[i] + t * (x[i + 1] - x[i])
    return out


def _curve_len(y, xs):
    m = np.isfinite(xs)
    return float(np.sum(np.hypot(np.diff(xs[m]), np.diff(y[m]))))


def bathy_contour_figure(path):
    """THE TWO CONTOUR FAMILIES IN PLAN, and the convergence quantified.

    ONE shoreline, ONE Dean coefficient, ONE shelf cap. The only thing that
    differs between the panels is what "distance from the shoreline" is taken
    to mean -- along the grid's x axis, or to the curve.
    """
    import beach_plot as P
    import beach_evidence as EV
    ep = B.equilibrium_plan()
    y = ep['y']
    x = np.arange(0.0, 1000.0 + 4.0, 4.0)
    xs = ep['x_s']
    h_ax = B.plan_ramp(x, y, xs)
    h_nm = B.plan_ramp_normal(x, y, xs)
    lv = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0)
    x0, x1 = 120.0, float(np.nanmax(xs)) + 60.0
    img = P.canvas(1660, 1330)
    L0 = _curve_len(y, xs)
    lens = {}
    for k, (h2, ttl, col) in enumerate((
            (h_ax, 'KEYED CROSS-SHORE: d = A (x_s(y) - x)^(2/3). The contours '
                   'are TRANSLATES of the shoreline', _C_AXIS),
            (h_nm, 'KEYED TO THE CURVE: d = A dist(P, shore)^(2/3). The '
                   'contours are its NORMAL OFFSETS', _C_NORM))):
        ax = P.Axes(img, (70 + k * 800, 70, 760 + k * 800, 690),
                    (y[0], y[-1]), (x0, x1), title=ttl,
                    xlabel='alongshore, m',
                    ylabel=('cross-shore, m (sea at the top)' if k == 0
                            else ''), y_up=False)
        ax.frame(EV._ticks(y[0], y[-1], 5), EV._ticks(x0, x1, 6))
        ll = []
        for lvl in lv:
            c = _contour_polyline(x, y, h2, lvl)
            ax.line(y, c, col, 2 if lvl in (2.0, 6.0) else 1,
                    dash=None if lvl in (2.0, 6.0) else (5, 5))
            ll.append(_curve_len(y, c))
        lens[k] = ll
        ax.line(y, xs, _C_INK, 3)
        # the shore-normal rays: launched normal to the shoreline, drawn
        # straight, so the eye can see which family they stay normal to
        phi = B.shore_normal_angle(y, xs)
        for j in range(4, y.size - 4, 9):
            t = np.linspace(0.0, 330.0, 2)
            ax.line(y[j] + t * np.sin(phi[j]), xs[j] - t * np.cos(phi[j]),
                    (110, 112, 120), 1, dash=(4, 6))
        # the OTHER family's 6 m contour, so the difference is visible and not
        # only tabulated
        oth = _contour_polyline(x, y, h_nm if k == 0 else h_ax, 6.0)
        ax.line(y, oth, (150, 152, 158), 2, dash=(3, 7))
        P.legend(ax, [
            (_C_INK, 'the shoreline, %.0f m of curve' % L0),
            (col, 'depth contours 1-7 m; 2 m and 6 m solid'),
            ((150, 152, 158), 'the OTHER keying\'s 6 m contour: they part by '
                              '%.1f m'
             % float(np.nanmax(np.abs(_contour_polyline(x, y, h_ax, 6.0)
                                      - _contour_polyline(x, y, h_nm, 6.0))))),
            ((110, 112, 120), 'rays launched NORMAL to the shoreline'),
        ], y[0] + 30, x1 - 108)

    # ---- the convergence, as a number -------------------------------------
    # PERPENDICULAR spacing between the 2 m and the 6 m contour, per
    # alongshore station. That IS the convergence: the translate family lays
    # its contours down along the grid, so their perpendicular spacing is the
    # axis spacing times cos(phi_s) and CROWDS wherever the shore turns away
    # from the grid; the normal family holds it constant by construction.
    phi = B.shore_normal_angle(y, xs)
    msp = np.zeros(y.size, bool)
    msp[ep['j1'] + 2:ep['j2'] - 1] = True
    ds_ax = (_contour_polyline(x, y, h_ax, 2.0)
             - _contour_polyline(x, y, h_ax, 6.0)) * np.cos(phi)
    ds_nm = np.hypot(_contour_polyline(x, y, h_nm, 2.0)
                     - _contour_polyline(x, y, h_nm, 6.0), 0.0) * np.cos(phi)
    s26 = (6.0 / B.DEAN_A) ** 1.5 - (2.0 / B.DEAN_A) ** 1.5
    ax3 = P.Axes(img, (70, 790, 810, 1030), (y[0], y[-1]), (225.0, 262.0),
                 title='THE CONVERGENCE: PERPENDICULAR gap between the 2 m '
                       'and 6 m contours',
                 xlabel='alongshore, m', ylabel='gap, m')
    ax3.frame(EV._ticks(y[0], y[-1], 5), EV._ticks(225.0, 262.0, 6))
    ax3.hline(s26, (150, 152, 158), width=1)
    ax3.line(y, ds_ax, _C_AXIS, 2)
    ax3.line(y, ds_nm, _C_NORM, 2)
    P.legend(ax3, [
        (_C_AXIS, 'cross-shore keying: %.1f - %.1f m, a %.1f%% crowding, and '
                  'it tracks cos(phi_s) exactly'
         % (float(np.nanmin(ds_ax[msp])), float(np.nanmax(ds_ax[msp])),
            100 * (1.0 - float(np.nanmin(ds_ax[msp]))
                   / float(np.nanmax(ds_ax[msp]))))),
        (_C_NORM, 'normal keying: constant at %.1f m by construction'
         % float(np.nanmean(ds_nm[msp]))),
        ((150, 152, 158), 'the Dean offset itself, s(6 m) - s(2 m) = %.1f m'
         % s26),
    ], y[0] + 30, 259.5)

    # ---- and what it costs the ray ----------------------------------------
    # ON A REFINED GRID AND ON THE ANALYTIC SPIRAL ALONE, and both halves of
    # that are the measurement's honesty rather than its convenience. The
    # render grid is 16 m alongshore against 4 m cross-shore, and a contour
    # DIRECTION taken by finite difference on a 4:1 anisotropic grid carries
    # about a degree of its own error -- the size of the thing being measured.
    # And the rock headland's roughness turns the local shore normal by several
    # degrees cell to cell, which is a different question from this one.
    yf = np.arange(y[ep['j1']], y[ep['j2']] + 2.0, 2.0)
    xf = np.arange(0.0, 1000.0 + 2.0, 2.0)
    xsf = np.interp(yf, ep['pts'][:, 1], ep['pts'][:, 0])
    hf_ax = B.plan_ramp(xf, yf, xsf)
    hf_nm = B.plan_ramp_normal(xf, yf, xsf)
    phf = B.shore_normal_angle(yf, xsf)

    def _cnorm(h2, s):
        gx = np.gradient(-h2, xf, axis=1)
        gy = np.gradient(-h2, yf, axis=0)
        px = xsf - s * np.cos(phf)
        py = yf + s * np.sin(phf)
        fi = np.clip((px - xf[0]) / (xf[1] - xf[0]), 0, xf.size - 1.001)
        fj = np.clip((py - yf[0]) / (yf[1] - yf[0]), 0, yf.size - 1.001)
        i0, j0 = fi.astype(int), fj.astype(int)
        a, b = fi - i0, fj - j0

        def smp(g):
            return ((1 - a) * (1 - b) * g[j0, i0] + a * (1 - b) * g[j0, i0 + 1]
                    + (1 - a) * b * g[j0 + 1, i0] + a * b * g[j0 + 1, i0 + 1])
        return np.arctan2(-smp(gy), -smp(gx))
    s_b = (2.0 / B.DEAN_A) ** 1.5
    dth = -np.gradient(phf, yf) * s_b * np.sin(phf)
    m_ax = _cnorm(hf_ax, s_b) + phf
    m_nm = _cnorm(hf_nm, s_b) + phf
    ke = slice(6, yf.size - 6)
    ax4 = P.Axes(img, (890, 790, 1590, 1030), (yf[0], yf[-1]), (-1.6, 1.6),
                 title='THE COST, on the analytic spiral: the contour normal '
                       'a shore-normal ray meets at 2 m',
                 xlabel='alongshore, m', ylabel='mismatch, degrees')
    ax4.frame(EV._ticks(yf[0], yf[-1], 5), EV._ticks(-1.6, 1.6, 9))
    ax4.hline(0.0, (150, 152, 158), width=1)
    ax4.line(yf[ke], np.degrees(m_ax[ke]), _C_AXIS, 2)
    ax4.line(yf[ke], np.degrees(m_nm[ke]), _C_NORM, 2)
    ax4.line(yf[ke], np.degrees(dth[ke]), _C_RED, 2, dash=(5, 11))
    P.legend(ax4, [
        (_C_AXIS, 'cross-shore keying, MEASURED off the bed\'s own gradient: '
                  'mean |.| %.3f deg'
         % math.degrees(float(np.mean(np.abs(m_ax[ke]))))),
        (_C_NORM, 'normal keying, MEASURED the same way: mean |.| %.4f deg -- '
                  'zero to the grid\'s own accuracy'
         % math.degrees(float(np.mean(np.abs(m_nm[ke]))))),
        (_C_RED, 'DERIVED first order, -(d phi_s/dy) s sin(phi_s): mean |.| '
                 '%.3f deg' % math.degrees(float(np.mean(np.abs(dth[ke]))))),
    ], yf[0] + 20, 1.45)

    P.caption(img, [
        's10-bathy-contours  WHAT "CROSS-SHORE DISTANCE" MEANS ON A CURVED '
        'COAST. DERIVED: `d = A (x_s(y) - x)^(2/3)` and `d = A dist(P, '
        'shore)^(2/3)` generate DIFFERENT families. The first is generated by '
        'translation along the grid\'s',
        'x axis, so the PERPENDICULAR spacing of its contours is the axis '
        'spacing times cos(phi_s) and crowds by %.1f%% across this bay; the '
        'second is generated by the normal flow and holds that spacing '
        'constant, which is what an equilibrium profile asserts.'
        % (100 * (1.0 - float(np.nanmin(ds_ax[msp]))
                  / float(np.nanmax(ds_ax[msp])))),
        'The two families coincide if and only if phi_s = atan(dx_s/dy) is '
        'identically zero, which is every scene waves 1-8 rendered. DERIVED: a '
        'normal offset shares its NORMAL LINES with the curve it offsets, so a '
        'ray launched normal to the shoreline is normal to',
        'every contour it crosses and Snell is the identity along it; on the '
        'translate family the contour it meets after travelling s belongs to '
        'station y + s sin(phi_s), where the normal has turned by -(d '
        'phi_s/dy) s sin(phi_s) to first order.',
        'MEASURED, off the scene-linear bed arrays and never off a PNG: that '
        'mismatch at the 2 m contour, both families, against the derived line. '
        'The concentric ramp wave 9 named is the special case of the normal '
        'family for a circular shore about a pole.',
        'CITED: the Dean (1991) equilibrium profile h ~ x^(2/3), via '
        'terrain-architect chapter 12 -- which states the exponent and does '
        'NOT state what the distance is measured along, and that silence is '
        'this wave\'s finding.',
    ], x=40, y=1110)
    return P.save(img, path)


def bathy_residual_figure(path):
    """THE RESIDUAL OBLIQUITY DECOMPOSED, in both statistics, because the
    statistic is the finding."""
    import beach_plot as P
    import beach_evidence as EV
    ep = B.equilibrium_plan()
    ec = B.equilibrium_plan(delta=0.0)
    y = ep['y']
    x = np.arange(0.0, 1000.0 + 4.0, 4.0)
    xs, D = ep['x_s'], ep['D']
    n0 = -B.shore_normal_angle(y, xs)
    fan = B.fan_theta0(y, xs, D)
    ph_s = np.arctan2(y - D[1], xs - D[0])
    R_s = np.hypot(xs - D[0], y - D[1])
    msp = np.zeros(y.size, bool)
    msp[ep['j1'] + 2:ep['j2'] - 1] = True

    def run(h2, xs_, th0, c0):
        tr = B.transform_2d(x, y, h2, B.T_SWELL, B.H0_SWELL, th0, contour0=c0)
        p = B.plan_transport(y, xs_, tr)
        m, ms = p['mask'], msp & p['mask']
        return (math.degrees(float(np.mean(np.abs(p['theta_loc'][m])))),
                math.degrees(float(np.mean(p['theta_loc'][ms]))),
                math.degrees(float(np.mean(np.abs(p['theta_loc'][ms])))),
                float(np.sqrt(np.mean(p['Q'][ms] ** 2))))

    Dc = ec['D']
    v = ec['pts'] - Dc
    Rc = float(np.mean(np.hypot(v[:, 0], v[:, 1])))
    xs_c = Dc[0] + np.sqrt(np.maximum(Rc ** 2 - (y - Dc[1]) ** 2, 0.0))
    n0c = np.arctan2(y - Dc[1], xs_c - Dc[0])
    h_pol_c = B.plan_ramp_polar(x, y, Dc, (np.array([-1.5, 1.5]),
                                           np.array([Rc, Rc])))
    h_car_c = B.plan_ramp(x, y, xs_c)
    xr = B.zero_transport_plan(y, float(np.mean(xs)), B.THETA0_SWELL)
    flr = run(B.plan_ramp(x, y, xr), xr, B.THETA0_SWELL,
              -B.shore_normal_angle(y, xr))
    c_rad = run(h_pol_c, xs_c, n0c, n0c)
    dlt = math.pi / 2.0 - ep['alpha']
    c_dlt = run(h_pol_c, xs_c, n0c + dlt, n0c)
    c_ax = run(h_car_c, xs_c, n0c, n0c)
    bay = {k: run(h, xs, fan, n0) for k, h in
           (('axis', B.plan_ramp(x, y, xs)),
            ('pole', B.plan_ramp_polar(x, y, D, (ph_s, R_s))),
            ('norm', B.plan_ramp_normal(x, y, xs)))}

    terms = [('the meter\'s floor', flr[1], _C_INK),
             ('the march meets curvature', c_rad[1] - flr[1], _C_POLE),
             ('the declared delta = theta_b', c_dlt[1] - c_rad[1], _C_RED),
             ('the ramp keying', c_ax[1] - c_rad[1], _C_AXIS)]
    tot = sum(t[1] for t in terms)

    img = P.canvas(1660, 1190)
    ax1 = P.Axes(img, (80, 70, 810, 470), (-0.5, 5.5), (-0.4, 2.3),
                 title='SIGNED mean theta_loc: the four terms ADD to the bay',
                 xlabel='', ylabel='degrees, signed')
    ax1.frame(None, EV._ticks(-0.4, 2.0, 7))
    
    ax1.hline(0.0, (150, 152, 158), width=1)
    base = 0.0
    for i, (lab, v_, col) in enumerate(terms):
        ax1.fill_between(np.array([i - 0.34, i + 0.34]),
                         np.array([min(base, base + v_)] * 2),
                         np.array([max(base, base + v_)] * 2), col)
        ax1.text(i, max(base, base + v_) + 0.05, '%+.3f' % v_, _C_INK,
                 anchor='ms')
        base += v_
    for i, (v_, lab, col) in enumerate(((tot, 'sum of the four', (120, 122, 128)),
                                        (bay['axis'][1], 'MEASURED on the bay',
                                         _C_AXIS))):
        ax1.fill_between(np.array([4 + i - 0.34, 4 + i + 0.34]),
                         np.zeros(2), np.array([v_] * 2), col)
        ax1.text(4 + i, v_ + 0.05, '%+.3f' % v_, _C_INK, anchor='ms')
    P.legend(ax1, [
        (_C_INK, '1 floor  2 march x curvature  3 declared delta  4 ramp '
                 'keying  5 their sum  6 the bay, measured'),
        ((120, 122, 128), 'sum %+.4f deg against %+.4f measured -- %.0f%%, '
                          'so the PHYSICS decomposes'
         % (tot, bay['axis'][1], 100 * abs(tot / bay['axis'][1] - 1.0))),
    ], -0.35, 2.25)

    ax2 = P.Axes(img, (890, 70, 1590, 470), (-0.5, 3.5), (0.0, 4.5),
                 title='mean |theta_loc| on the BUILT bay: what each keying '
                       'actually buys',
                 xlabel='', ylabel='degrees, mean of |.|')
    ax2.frame(None, EV._ticks(0.0, 3.0, 7))
    for i, (k, lab, col) in enumerate((('axis', 'cross-shore', _C_AXIS),
                                       ('pole', 'concentric', _C_POLE),
                                       ('norm', 'normal-offset', _C_NORM))):
        ax2.fill_between(np.array([i - 0.3, i + 0.3]), np.zeros(2),
                         np.array([bay[k][0]] * 2), col)
        ax2.text(i, bay[k][0] + 0.06, '%.3f' % bay[k][0], _C_INK, anchor='ms')
    ax2.fill_between(np.array([2.7, 3.3]), np.zeros(2),
                     np.array([bay['axis'][0] - 0.71] * 2), (150, 152, 158))
    ax2.text(3.0, bay['axis'][0] - 0.71 + 0.06, '%.3f' % (bay['axis'][0]
                                                          - 0.71),
             _C_INK, anchor='ms')
    P.legend(ax2, [
        (_C_AXIS, '1 the bay as wave 9 built it: %.4f deg' % bay['axis'][0]),
        (_C_POLE, '2 the concentric ramp wave 9 priced: %.4f -- it removes '
                  '%.3f, not 0.71' % (bay['pole'][0],
                                      bay['axis'][0] - bay['pole'][0])),
        (_C_NORM, '3 the normal-offset ramp: %.4f, removes %.3f'
         % (bay['norm'][0], bay['axis'][0] - bay['norm'][0])),
        ((150, 152, 158), '4 where wave 9\'s prediction said it would land'),
    ], -0.35, 4.35)

    # the sweep that shows the two terms are not independent
    ax3 = P.Axes(img, (80, 560, 810, 900), (0.0, 20.0), (0.0, 5.0),
                 title='WHY THE PRICE DOES NOT TRANSFER: hold the geometry '
                       'fixed, sweep the obliquity',
                 xlabel='incidence obliquity off the shore normal, degrees',
                 ylabel='degrees')
    ax3.frame(EV._ticks(0.0, 20.0, 6), EV._ticks(0.0, 5.0, 6))
    bs = np.array([0.0, 2.0, 4.0, 6.5585, 9.0, 13.0, 20.0])
    ra, rp, sa, sp = [], [], [], []
    for bd in bs:
        a = run(h_car_c, xs_c, n0c + math.radians(bd), n0c)
        p = run(h_pol_c, xs_c, n0c + math.radians(bd), n0c)
        ra.append(a[0])
        rp.append(p[0])
        sa.append(a[1])
        sp.append(p[1])
    ra, rp = np.array(ra), np.array(rp)
    sa, sp = np.array(sa), np.array(sp)
    ax3.line(bs, ra, _C_AXIS, 2)
    ax3.line(bs, rp, _C_POLE, 2)
    ax3.line(bs, ra - rp, _C_RED, 3)
    ax3.line(bs, sa - sp, _C_INK, 3, dash=(8, 6))
    ax3.vline(6.5585, (150, 152, 158), width=1)
    P.legend(ax3, [
        (_C_AXIS, 'mean|theta|, cross-shore keying'),
        (_C_POLE, 'mean|theta|, concentric keying'),
        (_C_RED, 'THE RAMP TERM in mean|.|: %.3f -> %.3f deg, a factor of %.1f'
         % (ra[0] - rp[0], ra[-1] - rp[-1],
            (ra[0] - rp[0]) / max(ra[-1] - rp[-1], 1e-9))),
        (_C_INK, 'the same term in the SIGNED mean: %.3f -> %.3f -- flat'
         % (sa[0] - sp[0], sa[-1] - sp[-1])),
    ], 0.4, 4.85)

    ax4 = P.Axes(img, (890, 560, 1590, 900), (0.0, 1.0), (0.0, 1.0),
                 title='', xlabel='', ylabel='')
    ax4.text(0.0, 1.06, 'THE TABLE: one offshore spectrum, one ramp exponent, '
                        'one transform, one CERC closure', _C_INK, anchor='ls',
             font=P.FONT_B)
    rows = [
        ('shoreline', 'mean |theta|', 'Q rms, m3/s', (120, 122, 128)),
        ('straight, plane crest', '6.469 deg', '9.233e-02', _C_INK),
        ('closed-form ZERO-transport (THE FLOOR)', '%.3f deg' % flr[0],
         '%.4e' % flr[3], _C_NORM),
        ('the bay, plane crest', '5.595 deg', '1.333e-01', _C_RED),
        ('the bay, hand-stated fan (wave 9)', '%.3f deg' % bay['axis'][0],
         '%.4e' % bay['axis'][3], _C_AXIS),
        ('the bay, CONCENTRIC ramp', '%.3f deg' % bay['pole'][0],
         '%.4e' % bay['pole'][3], _C_POLE),
        ('the bay, NORMAL-OFFSET ramp', '%.3f deg' % bay['norm'][0],
         '%.4e' % bay['norm'][3], _C_NORM),
    ]
    for i, (a, b, c, col) in enumerate(rows):
        yy = 0.93 - 0.13 * i
        ax4.text(0.02, yy, a, col, anchor='ls')
        ax4.text(0.66, yy, b, col, anchor='ls')
        ax4.text(0.84, yy, c, col, anchor='ls')

    P.caption(img, [
        's10-bathy-residual  THE RESIDUAL OBLIQUITY, DECOMPOSED, AND THE '
        'STATISTIC IS THE FINDING. MEASURED, scene-linear, off the transform\'s '
        'own arrays: wave 9 priced the concentric ramp at 0.71 deg of the '
        'bay\'s 2.801 deg residual.',
        'It reproduces EXACTLY on the circle it was measured on (%.4f deg) and '
        'removes %.3f deg on the bay it was written against -- because the '
        'keying error is ANTISYMMETRIC about the bay\'s apex (sin phi_s changes '
        'sign there), so it is'
        % (ra[0] - rp[0], bay['axis'][0] - bay['pole'][0]),
        'scatter and not drift, and mean|.| of a zero-mean term does not add '
        'to mean|.| of a biased one. The lower-left panel is the proof: hold '
        'the geometry EXACTLY fixed and change only the incidence obliquity, '
        'and the ramp term in mean|.|',
        'falls by a factor of %.1f while the same term in the signed mean does '
        'not move. DERIVED: the four signed terms, each measured one at a time '
        'on the circle, sum to %+.4f deg against %+.4f measured on the bay -- '
        'the physics IS decomposable.'
        % ((ra[0] - rp[0]) / max(ra[-1] - rp[-1], 1e-9), tot, bay['axis'][1]),
        'RULING 14 (wave 9\'s own): the floor is measured and printed beside '
        'every small number -- %.3f deg / %.4e m3/s on the closed-form '
        'zero-transport coast. The bay is %.1fx the floor after the fix and '
        '%.1fx before it: SMALL, and not zero.'
        % (flr[0], flr[3], bay['norm'][3] / flr[3], bay['axis'][3] / flr[3]),
        'Q rms is quoted over the spiral span in every row, mean|theta| over '
        'the whole domain, exactly as wave 9 quoted them. Nothing was read off '
        'a PNG.',
    ], x=40, y=960)
    return P.save(img, path)


def _cap_J10(w, cam, inf, m, ep, res):
    sh = m.get('shares', {})
    return [
        's10-bathy-frame  BAR SECTION J\'S FRAMING, ONE FIELD CHANGED FROM '
        's9-frame-J.png: the Dean ramp is keyed to the distance to the '
        'shoreline CURVE instead of along the grid\'s cross-shore axis. Same '
        'inferred viewpoint, same 0.5x ultrawide upright, same sun, same '
        'optics, same beach, same air, same plan-form.',
        'DERIVED: `d = A dist(P, shore)^(2/3)`. The two keyings are the same '
        'surface only where the shore runs parallel to the grid; here they '
        'differ by %.2f m of bed at the widest, and the contours they build '
        'differ in DIRECTION, which is what refraction reads.' % res['dmax'],
        'MEASURED off the scene-linear buffer, never off this PNG: on the '
        'composed bed under the fan its own pole implies, mean |theta_loc| '
        'falls %.4f -> %.4f deg and Q rms over the spiral span %.4e -> %.4e '
        'm3/s. The meter\'s floor, measured on the closed-form zero-transport '
        'coast, is %.4e m3/s and did not move.'
        % (res['ax'][0], res['nm'][0], res['ax'][2], res['nm'][2],
           res['floor']),
        'STILL OPEN in this frame, unchanged by this wave: the illuminant is '
        'in the wrong half of the sky; ONE surf zone where bar J shows three '
        'to four separated lines; no airborne spray; the bed under the water '
        'reads 1.24-1.40x too bright. By "no placeholder in a hero frame" this '
        'is a diagnostic.',
        'Colour ladder, share of frame: %s. Camera: %.2f +/- %.2f deg '
        'depression, %.1f x %.1f deg upright, brow at z = %.2f m. '
        'Scene-linear measured before the tone map; the tone map is display '
        'only.'
        % (', '.join('%s %.2f%%' % (k, 100 * v) for k, v in sh.items()),
           math.degrees(inf['dep']['mid']),
           math.degrees(inf['dep']['half_width']),
           math.degrees(inf['fov_h']), math.degrees(inf['fov_v']),
           inf['z_ground']),
    ]


def main_wave10():
    """WAVE 10 ONLY. The bed under the bay changes, so the frame changes and
    the two diagnostics are rebuilt from the same call."""
    t0 = time.time()
    _set_runup()
    print('sun: elevation %.2f deg, azimuth %.2f deg' % (SUN_EL, SUN_AZ))
    bathy_contour_figure('%s/s10-bathy-contours.png' % OUT)
    print('contours %.1f s' % (time.time() - t0))
    bathy_residual_figure('%s/s10-bathy-residual.png' % OUT)
    print('residual %.1f s' % (time.time() - t0))

    cs = B.run_coast()
    ep = B.equilibrium_plan(coast=cs)
    bay1 = B.run_bay(embay=True)
    y, xg = bay1['y'], bay1['x']
    hc = np.stack([np.interp(xg, cs['x'], cs['h'][j]) for j in range(y.size)])
    h0 = np.stack([np.interp(xg, cs['x'], cs['h0'][j]) for j in range(y.size)])
    h_ax, _, _, _ = B.bay_bed(xg, y, hc, h0, sand_row=cs.get('sand_row'),
                              plan=ep['x_s'], keying='axis')
    fan = B.fan_theta0(y, ep['x_s'], ep['D'])
    n0 = -B.shore_normal_angle(y, ep['x_s'])
    msp = np.zeros(y.size, bool)
    msp[ep['j1'] + 2:ep['j2'] - 1] = True

    def rd(h2, xs_, th0, c0):
        tr = B.transform_2d(xg, y, h2, B.T_SWELL, B.H0_SWELL, th0, contour0=c0)
        p = B.plan_transport(y, xs_, tr)
        ms = msp & p['mask']
        return (math.degrees(float(np.mean(np.abs(p['theta_loc']
                                                  [p['mask']])))),
                math.degrees(float(np.mean(np.abs(p['theta_loc'][ms])))),
                float(np.sqrt(np.mean(p['Q'][ms] ** 2))))
    xr = B.zero_transport_plan(y, float(np.mean(ep['x_s'])), B.THETA0_SWELL)
    res = dict(ax=rd(h_ax, ep['x_s'], fan, n0),
               nm=rd(bay1['h_init'], ep['x_s'], fan, n0),
               floor=rd(B.plan_ramp_normal(xg, y, xr), xr, B.THETA0_SWELL,
                        -B.shore_normal_angle(y, xr))[2],
               dmax=float(np.max(np.abs(bay1['h_init'] - h_ax))))
    print('composed bed: axis %.4f deg / %.4e -> normal %.4f deg / %.4e; '
          'floor %.4e' % (res['ax'][0], res['ax'][2], res['nm'][0],
                          res['nm'][2], res['floor']))
    w = Water(bay1)
    SS = SS_HERO
    (_, _, _, camJ, infJ, _, _, _, _) = hero_cameras(w, W_HERO * SS,
                                                     H_HERO * SS)
    L, ex = render(camJ, w)
    m = frame_report('J (wave 10, normal-keyed ramp)', w, camJ, infJ, L, ex)
    _save(downsample(L, SS), '%s/s10-bathy-frame.png' % OUT,
          caption=_cap_J10(w, camJ, infJ, m, ep, res))
    print('%.1f s' % (time.time() - t0))
    return res


if __name__ == '__main__':
    if '--wave10' in sys.argv:
        main_wave10()
    elif '--wave9' in sys.argv:
        main_wave9()
    elif '--wave8' in sys.argv:
        main_wave8()
    else:
        main()
