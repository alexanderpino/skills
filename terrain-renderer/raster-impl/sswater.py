"""The screen-space water pass: one fullscreen triangle, in the chapter's terms.

`12-water-rendering.md`, *Screen-space water: the fullscreen-triangle pass*, is
specified precisely enough to implement and had, before this file, no code
behind it. This is that pass. The chapter's four numbered steps are the four
blocks of `water_pass` below, in order, with the chapter's own names on them.

WHAT IS THE CHAPTER'S SPECIFICATION
  1. "A single fullscreen triangle covers the screen" -- `fullscreen_triangle`
     emits the three oversized verts from the vertex ID with the chapter's own
     bit arithmetic, and `rasterize` runs a real coverage test on them. Not a
     `for pixel in image`: the triangle is drawn.
  2. "One *triangle*, not a quad -- community canon with a real reason": the
     quad's shared diagonal cuts 2x2 pixel quads in half, so the rasterizer runs
     partially-covered quads twice along the seam. `helper_lane_audit` MEASURES
     that instead of repeating it, and the answer is in the README.
  3. The pixel shader: view ray; analytic plane hit `t = (h - camPos)/rayDir`
     with the three named guards; depth reject against the opaque buffer; shade.
  4. "traversal distance from scene depth vs `t` for absorption" -- the column
     length is `t_scene - t` along the STRAIGHT ray, which is what the depth
     buffer can answer and what the chapter asks for.

WHAT IS MINE
  * The optical composition below is assembled from `optics.py` and
    `atmosphere.py` across an import; the chapter says "everything in Shading
    and optics applies unchanged at the hit point" and does not write the
    composition out, so the composition is mine and every leg of it is named.
  * `upwelling='directional'` vs `'diffuse'` is my split, and it is the
    experiment: see below.
  * NOT BUILT, and marked rather than faked: wave normal cascades (the chapter's
    "two to four scrolling layers" would need a noise-derived normal map, and
    `render.py`'s header rule is no texture, no Voronoi, no noise -- an analytic
    Gerstner sum is the chapter's own stated substitute and is `field.py`'s job,
    not this file's); per-pixel raymarching of a displaced surface; the
    underwater branch; SSR. Each is listed in the README with what it would take.

THE EXPERIMENT, AND WHY THERE ARE TWO UPWELLING MODES
The chapter's factorisation trap bites a term that is an AVERAGE OVER
DIRECTIONS, and a screen-space pass has a view direction, so where the average
enters is a design decision the chapter does not make for you:

  'directional'  The physically careful pass. The bed's own light is attenuated
                 over the ray's OWN path -- `exp(-a*L)`, no table, exactly the
                 case the chapter calls "right for a *single* ray, whose mu is
                 known". The LUT is then read in the only two places that really
                 are angular averages: the sky's entry leg into the column, and
                 the bed<->underside trap gain.
  'diffuse'      The pass a table-indexed water shader actually ships: the whole
                 upwelling is one column term, `L_bed * T_esc[tau]`, which is
                 `optics.wbounce_of` with the integral replaced by a fetch. This
                 is the chapter's named temptation, "A depth-indexed absorption
                 table times a constant exit factor", drawn at full size.

Running the same frame in both, against both bakes, is how a 19.4% term-level
error is priced in pixels -- which is the chapter's own warning ("Check the
term, not the chain") turned into a measurement.

MEASURE IN SCENE-LINEAR. Everything returned by this file is radiance. The tone
map lives in `evidence.py` and nothing measured ever goes through it.
"""
import sys as _sys
import os as _os

import numpy as np

_REF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                     '..', 'reference-impl')
if _REF not in _sys.path:
    _sys.path.insert(0, _REF)

import optics as OPT                                            # noqa: E402
import atmosphere as ATM                                        # noqa: E402

import scene as SC                                              # noqa: E402
import lut as LUT                                               # noqa: E402

EPS_RAYZ = 1e-6      # the chapter's `|rayDir.y| < eps` guard, on this file's z.
                     # Sized from the datum tolerance it implies: at |dz| = 1e-6
                     # and an eye 1.62 m above the plane, t = 1.62e6 m, which is
                     # already 400x the scene's own far shelf. Anything smaller
                     # is a hit at a distance no depth buffer can represent.


# ------------------------------------------------------ 1. THE TRIANGLE ITSELF
def fullscreen_triangle():
    """The chapter's vertex shader, in three lines and with nothing bound.

        uv  = float2((id << 1) & 2, id & 2);            // (0,0) (2,0) (0,2)
        pos = float4(uv.x*2 - 1, 1 - uv.y*2, 0, 1);     // (-1,1)..(3,-3)

    Returns (pos_ndc (3,2), uv (3,2)). There is no vertex buffer and no index
    buffer, which is the chapter's point: `Draw(3)`."""
    ids = np.arange(3)
    uv = np.stack([(ids << 1) & 2, ids & 2], axis=1).astype(float)
    pos = np.stack([uv[:, 0] * 2.0 - 1.0, 1.0 - uv[:, 1] * 2.0], axis=1)
    return pos, uv


def screen_quad():
    """The thing the chapter says not to draw, for the audit below: two triangles
    over the unit square, sharing the (-1,-1)-(1,1) diagonal."""
    v = np.array([[-1., 1.], [1., 1.], [-1., -1.], [1., -1.]])
    return v, [(0, 1, 2), (1, 3, 2)]


def rasterize(pos, uv, res=SC.RES):
    """A real coverage test at pixel centres: edge functions, barycentrics,
    perspective-free interpolation (w = 1 for all three verts, as the chapter's
    VS emits). Returns (covered, uv_interp).

    This is not decoration. If the oversized triangle did NOT cover every pixel
    the pass would have holes, and the claim "the oversized tri clips to exactly
    the screen" is a claim about arithmetic that is cheaper to check than to
    trust -- `validate_raster.py` checks it at three resolutions and three
    aspect ratios."""
    X, Y = SC.pixel_ndc(res)
    p0, p1, p2 = pos
    d = ((p1[0] - p0[0]) * (p2[1] - p0[1])
         - (p2[0] - p0[0]) * (p1[1] - p0[1]))
    w0 = ((p1[0] - X) * (p2[1] - Y) - (p2[0] - X) * (p1[1] - Y)) / d
    w1 = ((p2[0] - X) * (p0[1] - Y) - (p0[0] - X) * (p2[1] - Y)) / d
    w2 = 1.0 - w0 - w1
    cov = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    U = w0 * uv[0, 0] + w1 * uv[1, 0] + w2 * uv[2, 0]
    V = w0 * uv[0, 1] + w1 * uv[1, 1] + w2 * uv[2, 1]
    return cov, np.stack([U, V], axis=-1)


def helper_lane_audit(res=SC.RES):
    """The chapter's justification for one triangle rather than two, MEASURED.

    A GPU shades in 2x2 pixel quads: any quad a primitive touches at all runs
    all four lanes, and the lanes outside the primitive are helper lanes whose
    work is thrown away. The claim is that a quad's shared diagonal "cuts 2x2
    pixel quads in half, so the rasterizer runs partially-covered quads and
    redundant helper lanes twice along the seam".

    Returns a dict of counts. `lanes` is 4 x (number of primitive-quad pairs
    with any coverage) -- the exact thing a GPU pays."""
    w, h = res
    qw, qh = (w + 1) // 2, (h + 1) // 2
    X, Y = SC.pixel_ndc(res)

    def cover(v, tri):
        p0, p1, p2 = v[tri[0]], v[tri[1]], v[tri[2]]
        d = ((p1[0] - p0[0]) * (p2[1] - p0[1])
             - (p2[0] - p0[0]) * (p1[1] - p0[1]))
        a = ((p1[0] - X) * (p2[1] - Y) - (p2[0] - X) * (p1[1] - Y)) / d
        b = ((p2[0] - X) * (p0[1] - Y) - (p0[0] - X) * (p2[1] - Y)) / d
        c = 1.0 - a - b
        return (a >= 0) & (b >= 0) & (c >= 0)

    def quads_touched(cv):
        q = np.zeros((qh, qw), bool)
        for dy in (0, 1):
            for dx in (0, 1):
                s = cv[dy::2, dx::2]
                q[:s.shape[0], :s.shape[1]] |= s
        return q

    tpos, tuv = fullscreen_triangle()
    tri_cov = rasterize(tpos, tuv, res)[0]
    tq = quads_touched(tri_cov)

    qv, qtris = screen_quad()
    qcovs = [cover(qv, t) for t in qtris]
    qqs = [quads_touched(c) for c in qcovs]
    both = qqs[0] & qqs[1]
    return {
        'res': res, 'quads': qw * qh,
        'tri_pixels': int(tri_cov.sum()),
        'quad_pixels': int((qcovs[0] | qcovs[1]).sum()),
        'tri_quad_pairs': int(tq.sum()),
        'quad_quad_pairs': int(qqs[0].sum() + qqs[1].sum()),
        'seam_quads_run_twice': int(both.sum()),
        'tri_lanes': 4 * int(tq.sum()),
        'quad_lanes': 4 * int(qqs[0].sum() + qqs[1].sum()),
        'primitives': (1, 2),
    }


# ------------------------------------------------------------- 2. THE SHADING
def sky_dirs(d):
    """`atmosphere.sky` contracts against a flat list of directions; this is the
    only reshaping wrapper, so nothing else in the file has to know."""
    sh = d.shape[:-1]
    return ATM.sky(d[..., 0].ravel(), d[..., 1].ravel(),
                   d[..., 2].ravel()).reshape(sh + (3,))


def snell_mu(cos_a):
    """Water-side cosine for an air-side one, per channel. `optics.refract`
    solves the same law as a direction map; this is the scalar cosine form the
    slant paths want, and it is the SAME arithmetic (k = 1 - eta^2 sin^2) with
    eta = 1/n, which cannot reach the TIR branch from the air side."""
    s2 = np.clip(1.0 - np.asarray(cos_a, float) ** 2, 0.0, 1.0)[..., None]
    return np.sqrt(np.maximum(1.0 - s2 / OPT.IOR[None] ** 2, 0.0))


# The sun's own water-side cosine and the entry Fresnel: constants of the shoot,
# resolved once, exactly as `12`'s *What to pre-cook* rung "on load" says. Both
# come out of `atmosphere.SUN_DIR` and `optics.fresnel` and neither is written
# by hand.
COS_SUN = float(ATM.SUN_DIR[2])                 # cosine from the vertical
MU_SUN_W = np.reshape(snell_mu(np.array(COS_SUN)), 3)           # (3,)
T_ENTER_SUN = np.reshape(1.0 - OPT.fresnel(COS_SUN), 3)         # (3,)


def bed_radiance(dep3, esc, rt):
    """The in-water radiance of the Lambertian bed under `dep` metres of water,
    with the surface's trap closed. Every factor is named:

      beam   (1 - R_ext(sun)) * E_sun*cos_sun/pi, attenuated over the sun's own
             REFRACTED slant `dep/mu_sun_w` -- a single ray with a known mu, so
             `exp(-a L)` is exactly right here and no table is involved.
      sky    (1 - R_ext_diffuse) * E_sky/pi, attenuated over the column by the
             ENTRY-weighted diffuse transmittance. That weight is not a free
             choice: by Helmholtz reciprocity the flux entering the water at
             water-side cosine mu is weighted by the same (1 - R_int(mu)) that
             governs escape, so the normalised down-leg transmittance is

                 T_dn(tau) = T_esc(tau) / (1 - R_int)

             -- the SAME integral, read again. Which is why the sky leg carries
             the factorisation error too, and why `diffuse` mode carries it
             twice. Checked in the suite: at tau = 0 this gives exactly
             1 - R_EXT and a white lossless bed composes to an albedo of 1.
      trap   1 / (1 - rho_bed * G_rt), the geometric series `optics.trap_gain`
             closes, with G_rt from the LUT.

    `esc`, `rt` are (...,3) from an `ExitLUT`. `dep3` is (...,3) in metres, PER
    CHANNEL -- the pass hands the same depth three times, `offline.py` hands
    three different ones because it refracts each band separately and a
    dispersive ray lands on a different patch of a sloping bed."""
    dep3 = np.asarray(dep3, float)
    tsl = np.exp(-OPT.ABS[None] * dep3 / MU_SUN_W[None])
    beam = T_ENTER_SUN[None] * ATM.SUN_COL[None] * COS_SUN * tsl
    sky = ((1.0 - OPT.R_EXT[None]) * ATM.SKY_DECK[None]
           * esc / OPT.T_OUT_DIFFUSE[None])
    lb0 = SC.RHO_BED[None] * (beam + sky)
    return lb0 / (1.0 - SC.RHO_BED[None] * rt)


def water_shade(dirs, dep, path3, exitlut, upwelling='directional'):
    """The transmitted and reflected halves of a water pixel, in scene-linear
    radiance. `dirs` (...,3) view directions, `dep` (...) the column thickness
    the pixel's optical depth is taken from, `path` (...) the length of water the
    view ray actually crosses.

    Reflected half: the exact unpolarised Fresnel of `optics.fresnel` against
    `atmosphere.sky` mirrored in the datum normal (0,0,1). The sun's disc is
    inside `sky()`, so the specular road is a consequence and not a term.

    Transmitted half, `directional`: the emergent radiance along THIS ray,
        L_air = (1 - R_ext(theta_a)) * L_bed * exp(-a*path) / n^2
    with the 1/n^2 from `optics.out_of_water` -- the radiance law, not a fudge.
    Hemispherically this integrates to exactly `pi*L_bed*T_esc`, which is
    `optics.wbounce_of`; the suite pins that identity, because it is the bridge
    between this directional form and the `diffuse` one.

    Transmitted half, `diffuse`: L_air = L_bed * T_esc[tau], i.e. the whole
    upwelling from the column table. Lambertian emergent by assumption."""
    tau = OPT.ABS[None] * np.asarray(dep, float)[..., None]
    esc, rt = exitlut(tau)
    cos_a = np.clip(-dirs[..., 2], 0.0, 1.0)
    R = OPT.fresnel(cos_a)
    refl = dirs.copy()
    refl[..., 2] = -refl[..., 2]
    L_refl = R * sky_dirs(refl)
    L_bed = bed_radiance(np.repeat(np.asarray(dep, float)[..., None], 3, -1),
                         esc, rt)
    if upwelling == 'directional':
        att = np.exp(-OPT.ABS[None] * np.asarray(path3, float))
        L_up = OPT.out_of_water((1.0 - R) * L_bed * att)
    elif upwelling == 'diffuse':
        L_up = L_bed * esc
    else:
        raise ValueError(upwelling)
    return L_refl, L_up


# --------------------------------------------------------------- 3. THE PASS
def _ssr_refine(gbuf, d, t, dep0, mu_w, water, h_water, iters):
    """Screen-space refraction as a fixed point in the depth buffer.

    Refract the view ray at the datum (band 1 only -- one tap, as a shader
    does; the dispersive three-tap version is `offline.py`'s and costs three
    times the bandwidth), step to the estimated bed point, project it back to
    screen, re-sample the depth buffer there, and take the new column from that.
    Three things are guarded and each has bitten a real implementation:

      * a re-projection that lands OFF SCREEN -- keep the previous estimate,
        never wrap or clamp to an edge texel, which smears the frame border into
        the water;
      * a re-sample that lands on a texel ABOVE the datum (sky, or the post's
        proud part) -- keep the previous estimate;
      * a re-sample nearer than the water hit -- the same reject as step 3, and
        the reason it must be repeated is that the refracted tap is a DIFFERENT
        pixel with a different `t`.
    """
    res = gbuf['res']
    eye = gbuf['eye']
    cos_a = np.clip(-d[..., 2], 1e-9, 1.0)
    mu1 = mu_w[..., 1]
    # the refracted direction, in the datum's own frame: the horizontal part is
    # scaled by sin_w/sin_a and the vertical is -mu_w. `optics.refract` says the
    # same thing as a vector map; written out here because the pass has one
    # normal and can afford to.
    sin_a = np.sqrt(np.clip(1.0 - cos_a ** 2, 0.0, 1.0))
    scale = np.where(sin_a > 1e-9,
                     np.sqrt(np.clip(1.0 - mu1 ** 2, 0.0, 1.0)) / np.maximum(sin_a, 1e-9),
                     0.0)
    rd = np.stack([d[..., 0] * scale, d[..., 1] * scale, -mu1], axis=-1)
    Pw = eye[None, None] + t[..., None] * d

    dep = dep0.copy()
    for _ in range(max(1, int(iters))):
        B = Pw + rd * (dep / mu1)[..., None]
        col, row, _, ok = SC.project_to_pixel(
            B.reshape(-1, 3), res, gbuf['az'], gbuf['el'], gbuf['fov'], eye)
        col = np.clip(np.round(col), 0, res[0] - 1).astype(np.int64)
        row = np.clip(np.round(row), 0, res[1] - 1).astype(np.int64)
        z = gbuf['depth'][row, col]
        w = SC.unproject_depth(z)
        dirs_s = SC.ray_dirs(2.0 * (col + 0.5) / res[0] - 1.0,
                             1.0 - 2.0 * (row + 0.5) / res[1],
                             gbuf['az'], gbuf['el'], gbuf['fov'],
                             res[0] / res[1])
        f = SC.basis(gbuf['az'], gbuf['el'])[0]
        with np.errstate(divide='ignore', invalid='ignore'):
            ts = w / (dirs_s @ f)
        zs = eye[2] + ts * dirs_s[:, 2]
        newdep = (h_water - zs).reshape(dep.shape)
        good = ok.reshape(dep.shape) & (z.reshape(dep.shape) > 0) \
            & (newdep > 0) & np.isfinite(newdep) & water
        dep = np.where(good, newdep, dep)
    return dep, dep[..., None] / mu_w


def water_pass(gbuf, exitlut=None, upwelling='directional', h_water=SC.H_WATER,
               jitter_shader=None, traversal='straight', ssr_iters=3):
    """The chapter's pixel shader, its four steps in its own order.

    `gbuf` is what `scene.prepass` wrote: a reversed-Z DEPTH buffer and a
    scene-colour copy. This function reads NOTHING else about the scene -- no
    `opaque_hit`, no bed field, no analytic geometry beyond the water plane
    itself. That restriction is the whole meaning of "screen-space", and it is
    what makes the pass's disagreements with `offline.py` diagnostic.

    `jitter_shader` reproduces the chapter's second named trap: a TAA jitter the
    depth prepass applied and the water pass did not. Pass the prepass's own
    jitter to match; pass None while the prepass jittered to see the mismatch."""
    if exitlut is None:
        exitlut = LUT.ExitLUT('joint')
    res = gbuf['res']
    eye, f = gbuf['eye'], SC.basis(gbuf['az'], gbuf['el'])[0]

    # -- the triangle. Coverage decides which pixels the shader runs on at all.
    tpos, tuv = fullscreen_triangle()
    cov, uv = rasterize(tpos, tuv, res)

    # -- STEP 1: the view ray, from the camera basis and pixel NDC.
    ndc_x = uv[..., 0] * 2.0 - 1.0
    ndc_y = 1.0 - uv[..., 1] * 2.0
    if jitter_shader is not None:
        jx, jy = jitter_shader
        ndc_x = ndc_x + 2.0 * jx / res[0]
        ndc_y = ndc_y - 2.0 * jy / res[1]
    d = SC.ray_dirs(ndc_x, ndc_y, gbuf['az'], gbuf['el'], gbuf['fov'],
                    res[0] / res[1])

    # -- STEP 2: the analytic hit, with the chapter's three guards, explicit.
    dz = d[..., 2]
    parallel = np.abs(dz) < EPS_RAYZ                     # guard 1
    below = eye[2] < h_water                             # guard 3 (sign flip)
    with np.errstate(divide='ignore', invalid='ignore'):
        t = (h_water - eye[2]) / np.where(parallel, 1.0, dz)
    behind = t <= 0.0                                    # guard 2
    hit = cov & ~parallel & ~behind
    if below:
        # the underwater branch is NOT built; the guard exists so that a camera
        # placed below the datum fails loudly instead of drawing nonsense.
        raise NotImplementedError(
            'camPos below h_water: the chapter\'s underwater branch of the same '
            'triangle is not built here -- see README, `Not built`.')

    # -- STEP 3: depth reject, from the depth buffer and the depth convention.
    w_scene = SC.unproject_depth(gbuf['depth'])          # view depth, m
    cosf = d @ f                                         # ray/forward cosine
    with np.errstate(divide='ignore', invalid='ignore'):
        t_scene = w_scene / cosf
    t_scene = np.where(gbuf['depth'] > 0, t_scene, np.inf)
    occluded = t_scene < t
    water = hit & ~occluded

    # -- STEP 4: shade. Column length and vertical depth BOTH from the buffer.
    p_scene_z = eye[2] + t_scene * dz
    dep = np.clip(h_water - p_scene_z, 0.0, None)        # vertical column
    path = np.clip(t_scene - t, 0.0, None)               # "scene depth vs t"
    dep = np.where(water, dep, 0.0)
    path = np.where(water, path, 0.0)

    # -- THE TRAVERSAL DISTANCE, AND THE ONE PLACE THIS FILE DISAGREES WITH `12`.
    # The chapter's step 4 is literal: "traversal distance from scene depth vs
    # `t` for absorption", i.e. `t_scene - t`, the STRAIGHT ray. That is what
    # every screen-space water shader ships and it is what `traversal='straight'`
    # does. It is also wrong, and not slightly: the transmitted ray REFRACTS at
    # the datum, and the ray that actually crosses the column is the bent one.
    # At an air-side angle theta_a the two lengths are d/cos(theta_a) against
    # d/mu_w, and mu_w >= 1/n = 0.75 no matter how grazing theta_a gets -- so the
    # straight-ray length diverges at the horizon while the true one is bounded
    # by 1.33 d. Over this frame that is a factor of 4.5 at the far water.
    # `traversal='snell'` is the fix and it is one `sqrt`: the Snell cosine of
    # the view angle, per band, which `snell_mu` already computes for free.
    # Measured both ways in `validate_raster.py`; the numbers are in the README.
    #
    # `traversal='ssr'` goes one step further and is the chapter's own third
    # sentence in step 4 -- "refraction from the scene-color copy" -- taken
    # seriously: the pass refracts the view ray, projects the estimated bed hit
    # back to screen, and RE-SAMPLES the depth buffer there. Two or three taps,
    # a fixed point in the depth field, and no scene access at any point. This
    # is the only mode that can get the OPTICAL DEPTH right on a sloping bed,
    # and the chapter does not say to do it.
    mu_w = snell_mu(np.clip(-dz, 1e-9, 1.0))
    if traversal == 'straight':
        path3 = np.repeat(path[..., None], 3, axis=-1)
    elif traversal == 'snell':
        path3 = dep[..., None] / mu_w
    elif traversal == 'ssr':
        dep, path3 = _ssr_refine(gbuf, d, t, dep, mu_w, water, h_water,
                                 ssr_iters)
    else:
        raise ValueError(traversal)

    L = gbuf['color'].copy()
    if water.any():
        refl, up = water_shade(d[water], dep[water], path3[water], exitlut,
                               upwelling)
        L[water] = refl + up
    return {'color': L, 'water': water, 'dep': dep, 'path': path,
            'path3': path3, 'traversal': traversal,
            't': t, 't_scene': t_scene, 'dirs': d, 'cov': cov,
            'occluded': occluded & hit, 'tau': OPT.ABS[None] * dep[..., None],
            'mode': (exitlut.mode, upwelling)}
