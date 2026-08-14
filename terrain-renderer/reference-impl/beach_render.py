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
        self.dep_lut = np.geomspace(0.05, 20.0, 48)
        self.rho_lut = np.stack([
            OPT.rho_water(SAND_WET, math.sin(math.radians(SUN_EL)), float(dd),
                          absorb=self.io_clear['a'] + self.io_clear['b_b'])
            for dd in self.dep_lut])
        self.t_col = col['t_col']

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
_K0 = (2.0 * math.pi / B.T_SWELL) ** 2 / B.G
_TH0 = B.THETA0_SWELL


def free_surface(w, xw, yw, t=0.0):
    H = w.sample(xw, yw, w.H)
    S = w.sample(xw, yw, w.S)
    om = 2.0 * math.pi / B.T_SWELL
    eta = 0.5 * H * np.cos(S - om * t)
    far = 0.5 * B.H0_SWELL * np.cos(
        _K0 * (xw * math.cos(_TH0) + yw * math.sin(_TH0)) - om * t)
    f = np.clip((w.x[0] + 60.0 - xw) / 60.0, 0.0, 1.0)
    return eta * (1.0 - f) + far * f


def surface_slope(w, xw, yw, t=0.0, eps=1.0):
    """The RESOLVED slope of the free surface, by central difference at the
    grid's own scale. `eps` is one metre: finer than the 2 m cross-shore cell
    and far finer than the 30-90 m wavelengths, so this differentiates the
    interpolant rather than the noise."""
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
    E_up = E_dn_w * (R_col + rho_bed * t_col)
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

    # ---- the foam PLACEHOLDER, and the caption says so
    fb = w.sample(xw, yw, w.brk.astype(float))
    # PLACEHOLDER, and it is put on the CRESTS rather than over the whole
    # breaking band only because a uniform sheet is a worse placeholder, not
    # because anything here models where foam goes. See the caption.
    crest = np.clip(free_surface(w, xw, yw, t_now)
                    / np.maximum(0.25 * w.sample(xw, yw, w.H), 0.02), 0.0, 1.0)
    cov = (BO.foam_coverage(fb) * crest)[..., None]
    L_foam = (BO.FOAM_WHITE * E_DOWN_AIR / np.pi)[None, None]

    L = L_sky + L_glit + L_up + L_path
    L = L * (1.0 - cov) + L_foam * cov
    return dict(L=L, L_sky=L_sky, L_glit=L_glit, L_up=L_up, L_path=L_path,
                chord=chord, cov=cov[..., 0], lit=lit, cos_v=cos_v)


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


def _save(L, path, key=None, gamma=2.2):
    """DISPLAY ONLY, and nothing in this file reads back through it.

    A single exposure `key` and a gamma. No filmic curve, no local adaptation,
    no white balance: the standing ruling is that a ratio between two levels
    does not survive a display-referred tone curve, and every ratio this file
    reports is taken from `L` before this function is called. The one thing the
    curve is allowed to do is make the frame legible."""
    k = WHITE if key is None else key
    img = np.clip(L / max(k, 1e-9), 0.0, 1.0) ** (1.0 / gamma)
    Image.fromarray((img * 255.0 + 0.5).astype(np.uint8)).save(path)
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
    x_edge = 694.0
    cliff_j = float(w.sample(np.array([x_edge]), np.array([-500.0]), w.h)[0])
    # THE FRAMING IS CONSTRAINED BY THE LANDFORM AND THAT IS A FINDING, NOT A
    # COMPOSITION PROBLEM. Bar section J's photograph is taken from a HEADLAND,
    # with sea on three sides. Wave 3's coastal loop produced 46 m of plan
    # curvature over 1408 m of coast -- a nearly straight cliffed shore -- so
    # there is no headland in this bed to stand on, and an eye 1.7 m above a
    # flat coastal plain sees that plain fill every landward direction to the
    # horizon. The camera therefore looks WEST-NORTH-WEST, out over the water
    # with the coast receding on the right; that is the most J-like frame this
    # bed can give, and the gap between it and J is recorded in the README.
    az_j = math.radians(292.0)
    camJ = Camera((x_edge, -500.0, cliff_j + 1.7),
                  (x_edge + 800.0 * math.sin(az_j),
                   -500.0 + 800.0 * math.cos(az_j), cliff_j + 1.7 - 160.0),
                  48.0, W, H)
    LJ, exJ = render(camJ, w)
    frames['J'] = (LJ, exJ, camJ)

    # ---- K: the open sea and the glitter path, straight down the sun's
    # azimuth. The path runs from the horizon into the near field and its width
    # is measured in ANGLE, above, rather than in pixels here.
    az = math.radians(SUN_AZ)
    cliff_k = float(w.sample(np.array([x_edge]), np.array([0.0]), w.h)[0])
    camK = Camera((x_edge, 0.0, cliff_k + 1.7),
                  (x_edge + 300.0 * math.sin(az), 300.0 * math.cos(az),
                   cliff_k + 1.7 - 64.0), 34.0, W, H)
    LK, exK = render(camK, w)
    frames['K'] = (LK, exK, camK)

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

    # ---- write the frames
    gap = np.zeros((cvA['L'].shape[0], 8, 3))
    kA = _save(np.concatenate([cvA['L'], gap, cvB['L']], axis=1),
               '%s/s4-cuvette.png' % OUT)
    kJ = _save(downsample(LJ, SS), '%s/s4-bay-render.png' % OUT)
    kK = _save(downsample(LK, SS), '%s/s4-glitter-render.png' % OUT)
    print('exposure keys (99th pct of scene-linear): A %.4g  J %.4g  K %.4g'
          % (kA, kJ, kK))
    print('%.1f s' % (time.time() - t0))
    return dict(A=mA, glitter=grows, w=w, frames=frames, cvA=cvA, cvB=cvB)


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
        np.linspace(w.x[0] + 5, w.x[-1] - 5, 300),
        np.linspace(w.y[0] + 20, w.y[-1] - 20, 120)))
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
    print('  -> the linear surface is %.0fx too gentle. Section A\'s backlit '
          'face is a\n     NEAR-BREAKING geometry and the height field cannot '
          'reach it; the cuvette\n     below is the instrument the bar itself '
          'names, and it says so in its caption.'
          % (need / max(s.max(), 1e-9)))
    return float(s.max()), float(need)


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
                    ('shallow, d < 1.5 m, unbroken', (dep < 1.5) & (brk < 0.2)),
                    ('surf, breaking', brk > 0.8)):
        if sel.sum() > 30:
            v = np.median(Lw[sel], 0)
            print('     %-30s %s   2G/(R+B) %.4f'
                  % (nm, np.round(v, 4), 2 * v[1] / max(v[0] + v[2], 1e-9)))
    Pl = None
    hl = None
    print('     (wet/dry sand pair: albedo ratio %s, from optics.wet_albedo, '
          'no new constant)' % np.round(SAND_WET / SAND_DRY, 4))


def horizon_check(L, cam):
    """Bar section K2: the sea's radiance at grazing must approach the sky's
    reflected value CONTINUOUSLY, and a seam there is a tell at a glance."""
    D = cam.rays()
    up = D[..., 2] >= 0.0
    rows = np.where(up.any(1) != up.all(1))[0]
    j = int(np.argmax(up.sum(1) > 0))
    if j < 2 or j + 3 >= L.shape[0]:
        print('  -- horizon not in frame')
        return
    a = L[j - 3:j - 1].reshape(-1, 3).mean(0)       # sky side
    b = L[j + 1:j + 3].reshape(-1, 3).mean(0)       # sea side
    print('  -- the sea-sky horizon (bar K2)')
    print('     sky just above  %s' % np.round(a, 4))
    print('     sea just below  %s' % np.round(b, 4))
    print('     step, per channel  %s  (luminance ratio %.4f)'
          % (np.round(b / np.maximum(a, 1e-9), 4),
             float(b.mean() / max(a.mean(), 1e-9))))


if __name__ == '__main__':
    main()
