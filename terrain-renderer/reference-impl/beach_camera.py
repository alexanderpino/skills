"""beach_camera.py -- wave 7. WHERE THE PHOTOGRAPH WAS TAKEN FROM.

The sea reference carries four hyper-realism criteria and the
FIRST of them is unmet by every frame this project has drawn:

    FRAME TO MATCH. A reference render must be shot from a viewpoint one of the
    owner's photographs was taken from, at the same framing, so the two can sit
    side by side. A render at a viewpoint no photograph shares is illustration,
    not proof.

Bar sections J and K are the two cliff-top frames -- the embayment overview and
the open sea with the glitter path. NEITHER CARRIES EXIF, and neither photograph
is in this repository: what is available is the bar's frozen INVENTORY OF WHAT
IS IN EACH FRAME. The camera is therefore an INFERENCE, and this file is written
as one. Every parameter comes out with an INTERVAL, the interval's width is a
statement about the evidence rather than about the code, and the measurement
that would collapse it is named beside it.

THE THREE PARAMETERS COME FROM THREE DIFFERENT PIECES OF EVIDENCE, so their
uncertainties are independent rather than one blur:

  FIELD OF VIEW is QUANTIZED, and that is the single most useful fact here. The
      bar names the device -- iPhone 16 Pro -- and a phone has a small fixed set
      of focal lengths. The FOV is not a continuous unknown to be fitted; it is
      a choice among four, decided by the horizontal coverage the frame's
      CONTENT requires. Best determined of the three, and determined by the
      INSTRUMENT rather than by the picture.

  DEPRESSION is what the horizon's height in the frame buys, and it is the only
      one of the three the picture itself measures. Without the pixels it is
      BRACKETED rather than measured: the horizon must be in frame (an upper
      bound) and the named foreground must be in frame (a lower bound).

  EYE HEIGHT is NOT measured by the horizon, and saying so is worth more than
      any number in this file. The dip is 0.0293*sqrt(z) degrees: 0.117 deg at
      16 m, 0.278 deg at 90 m. The DIFFERENCE between a 16 m cliff and a 90 m
      one is a sixth of a degree -- about six pixel rows in a 4032-pixel upright
      frame, and far inside the tilt error of a hand-held phone. The dip is
      famous and it is useless at cliff heights. What DOES measure the eye
      height is the resolved SEPARATION of shore-parallel surf lines, which goes
      as z*s/D^2 and is a strong function of z. That instrument is derived in
      `line_separation` below and it has a closed-form ceiling.

NOTHING HERE IS CALIBRATED AGAINST A PHOTOGRAPH'S LEVELS. The standing ruling is
that geometry and ordering may be read off the owner's frames and radiometry may
not; every number in this file is an angle, a length or a count.
"""

import math

# =========================================================== the instrument
# An "equivalent focal length" is equivalent ON the 36 x 24 mm frame, and that
# is the only thing the number means. Nothing about the phone's own sensor size
# enters -- which is why the equivalence is quoted at all.
FRAME_35 = (36.0, 24.0)                 # mm
DIAG_35 = math.hypot(*FRAME_35)         # 43.267 mm

# The still frame's own aspect. A phone shoots 4:3 stills; UPRIGHT means the
# long side is vertical, which is what bar sections J and K both record.
STILL_ASPECT = 4.0 / 3.0

# iPhone 16 Pro. Four fixed 35-mm-equivalent focal lengths, and the bar names
# the device, so this is a PRIOR SUPPLIED BY THE BAR rather than a guess.
# THE FOV IS QUANTIZED AND THAT IS THE WHOLE VALUE OF THIS TABLE: a continuous
# fit to a frame nobody can measure would be worthless; a choice among four is
# a choice the frame's content can actually make.
LENSES = (
    (13.0, 'ultrawide 0.5x'),
    (24.0, 'main 1x'),
    (48.0, 'main, 2x sensor crop'),
    (120.0, 'tele 5x'),
)

# ========================================================= earth and horizon
R_EARTH = 6371008.8                     # m, IUGG mean radius
# Standard refraction as an effective radius. k is the refraction coefficient:
# a light ray curves with k times the earth's curvature, so the geometry is
# exact on a sphere of radius R/(1-k).
#
# THE VALUE IS PINNED BY A PUBLISHED TABLE RATHER THAN CHOSEN. The geometric dip
# is sqrt(2z/R) = 1.9261*sqrt(z_m) arcminutes; the refracted dip is that times
# sqrt(1-k); and Bowditch's dip table is 0.97*sqrt(h_ft) = 1.757*sqrt(z_m)
# arcminutes. The ratio 1.757/1.9261 = 0.9122 gives k = 0.1678. It is stated to
# four figures because it is a FIT TO A TABLE and not a physical constant --
# over a warm summer sea k runs toward zero and beyond it (looming), over a cold
# one it doubles, and the suite carries the sensitivity rather than the value.
REFRACTION_K = 0.1678
BOWDITCH_DIP_ARCMIN = 1.757             # per sqrt(metre); the table this fits


def equiv_fov(f_mm, aspect=STILL_ASPECT, diag=DIAG_35):
    """The three fields of view of a lens of 35-mm-equivalent focal length.

    The equivalence is on the DIAGONAL -- that is what makes it an equivalence
    across two different frame shapes -- so the diagonal FOV comes first and the
    two sides follow from the target frame's own aspect:

        tan(diag/2) = diag_35 / (2 f)
        long / diag = a / sqrt(a^2 + 1),   short / diag = 1 / sqrt(a^2 + 1)

    Getting this wrong on the LONG side instead of the diagonal is a 4% error in
    a 24 mm lens and a 10% error in a 13 mm one, which is why it is written out.
    """
    half_d = math.atan(diag / (2.0 * f_mm))
    a = float(aspect)
    n = math.hypot(a, 1.0)
    half_l = math.atan(math.tan(half_d) * a / n)
    half_s = math.atan(math.tan(half_d) * 1.0 / n)
    return dict(f=float(f_mm), diag=2.0 * half_d, long=2.0 * half_l,
                short=2.0 * half_s)


def portrait_fov(f_mm, aspect=STILL_ASPECT):
    """(vertical, horizontal) FOV in radians for an UPRIGHT frame.

    Upright puts the long side vertical. Both J and K are recorded upright, and
    it matters: the same lens held the other way gives a frame 1.33x wider and
    0.75x tall, which moves every content bound in this file."""
    fv = equiv_fov(f_mm, aspect)
    return fv['long'], fv['short']


def rectilinear_hfov(fov_v, aspect_wh):
    """The horizontal FOV of a rectilinear camera whose vertical FOV is fov_v.

    tan(h/2) = tan(v/2) * (W/H). NOT h = v * W/H, which is the mistake that
    makes a wide frame 12% too narrow at 90 deg."""
    return 2.0 * math.atan(math.tan(0.5 * fov_v) * aspect_wh)


def horizon_dip(z, refraction=True):
    """Angle of the visible horizon BELOW the astronomical horizontal, radians.

    Geometric: cos(dip) = R/(R+z). With standard refraction the ray curves the
    same way the earth does, at 1/k of the rate, so the exact geometry is
    recovered on a sphere of radius R/(1-k).

    THE POINT OF THIS FUNCTION IS THAT IT IS SMALL. It is quoted here so the
    suite can measure how small, and so nobody tries to invert it for the cliff
    height: it is a square root, so its SENSITIVITY to z falls as 1/sqrt(z) --
    at 16 m a 1 m error in the cliff moves the horizon by 0.004 deg."""
    r = R_EARTH / (1.0 - REFRACTION_K) if refraction else R_EARTH
    z = float(z)
    return math.acos(r / (r + z))


def horizon_range(z, refraction=True):
    """Great-circle distance to the visible horizon, m."""
    r = R_EARTH / (1.0 - REFRACTION_K) if refraction else R_EARTH
    return r * horizon_dip(z, refraction)


def range_at_depression(z, dep, refraction=True):
    """Distance along the sea surface to the point seen at depression `dep`.

    Exact on the sphere, which is the only way to say honestly how much the flat
    plane in `beach_render.trace` costs: solve for t on the ray, then convert
    the chord to arc. Returns math.inf at or above the horizon."""
    r = R_EARTH / (1.0 - REFRACTION_K) if refraction else R_EARTH
    if dep <= horizon_dip(z, refraction) - 1e-15:
        return math.inf
    a = r + z
    disc = (a * math.sin(dep)) ** 2 - (a * a - r * r)
    if disc < 0.0:
        return math.inf
    t = a * math.sin(dep) - math.sqrt(disc)
    return r * math.asin(min(1.0, t * math.cos(dep) / r))


def range_flat(z, dep):
    """The same distance on a FLAT sea: z / tan(dep). Diverges at the horizon."""
    if dep <= 1e-12:
        return math.inf
    return z / math.tan(dep)


# =================================================== the frame, and the horizon
# A rectilinear frame with vertical FOV `fov_v` and optical axis depressed by
# `delta`. Normalised image height v runs +1 at the TOP edge to -1 at the
# BOTTOM, and a ray at angle `alpha` ABOVE the axis lands at v = tan(alpha) /
# tan(fov_v/2). Everything below is that one relation, inverted in different
# directions.

def image_v(alpha, fov_v):
    """Normalised height (+1 top, -1 bottom) of a ray `alpha` above the axis."""
    return math.tan(alpha) / math.tan(0.5 * fov_v)


def frame_fraction(alpha, fov_v):
    """Fraction of the frame height from the TOP edge. 0 = top, 1 = bottom."""
    return 0.5 * (1.0 - image_v(alpha, fov_v))


def horizon_fraction(delta, fov_v, z):
    """Where the true horizon sits in the frame, as a fraction from the top.

    The horizon is `delta` above the axis (the axis is depressed by delta) minus
    its own dip."""
    return frame_fraction(delta - horizon_dip(z), fov_v)


def depression_from_horizon_fraction(f_h, fov_v, z):
    """INVERT the above: the depression a measured horizon row implies.

    This is the function the actual photograph would feed. One pixel row of a
    4032-tall frame is 0.026 deg at the ultrawide's 106.6 deg, so a horizon
    line read to +/- 5 rows fixes the depression to +/- 0.13 deg -- two orders
    better than the bracket this file has to use instead."""
    v = 1.0 - 2.0 * float(f_h)
    return math.atan(v * math.tan(0.5 * fov_v)) + horizon_dip(z)


def frame_edges(z, delta, fov_v, refraction=True):
    """Angles and sea ranges at the top and bottom edges of the frame."""
    top = delta - 0.5 * fov_v               # below horizontal; negative = sky
    bot = delta + 0.5 * fov_v
    return dict(
        top_angle=top, bot_angle=bot,
        top_range=range_at_depression(z, top, refraction) if top > 0 else math.inf,
        bot_range=range_at_depression(z, bot, refraction),
        bot_range_flat=range_flat(z, bot),
        horizon_in_frame=bool(top < horizon_dip(z, refraction) < bot),
    )


# ============================== the instrument that DOES measure the eye height
def line_separation(z, D, s):
    """Angular separation of two shore-parallel lines s apart, at range D.

    THE ONE THING IN A CLIFF-TOP FRAME THAT REPORTS ON THE EYE HEIGHT. Bar J
    records "three to four separated breaking lines" and bar I1 "two clearly
    separated lines of whitewater with a calm band between them": the lines are
    RESOLVED, and how far apart they look is

        d = atan(z/(D-s)) - atan(z/D)

    which in the small-angle limit is z*s/D^2 -- LINEAR in the eye height and
    quadratic in the range. A metre of extra cliff buys as much separation as
    taking a half-metre off the range at 700 m, which is why this and not the
    dip is the instrument."""
    D, s = float(D), float(s)
    if not (0.0 < s < D):
        raise ValueError('need 0 < s < D; got s=%g D=%g' % (s, D))
    return math.atan(z / (D - s)) - math.atan(z / D)


def separation_ceiling(D, s):
    """The LARGEST separation any eye height can give, and the height that does.

    Write the difference of arctangents as one arctangent:

        tan(d) = z*s / (D(D-s) + z^2)

    and maximise over z. The derivative vanishes at z* = sqrt(D(D-s)) -- the
    GEOMETRIC MEAN of the two ranges -- where

        tan(d_max) = s / (2 sqrt(D(D-s))).

    So there is a hard ceiling on how separated two surf lines can ever be made
    to look from a given distance, and it is reached at an eye height of order
    the range itself. Below z* the separation is essentially linear in z; above
    it the lines close up again as the view goes plan-like. Derived here rather
    than cited: it is two lines of calculus and no source states it."""
    D, s = float(D), float(s)
    z_star = math.sqrt(D * (D - s))
    return math.atan(s / (2.0 * z_star)), z_star


def eye_height_for_separation(D, s, dtheta):
    """Invert `line_separation` for z. Returns the SMALLER root, or None.

    tan(d) z^2 - s z + tan(d) D(D-s) = 0. Two roots, one on each side of z*;
    the smaller is the lowest eye that achieves the separation and is the one a
    cliff can plausibly supply. `None` when the demand exceeds the ceiling."""
    t = math.tan(dtheta)
    if t <= 0.0:
        return 0.0
    disc = s * s - 4.0 * t * t * D * (D - s)
    if disc < 0.0:
        return None
    return (s - math.sqrt(disc)) / (2.0 * t)


def plan_width(D, fov_h):
    """Ground width a horizontal FOV covers at range D, on the flat."""
    return 2.0 * D * math.tan(0.5 * fov_h)


def standoff_for_chord(W, fov_h):
    """How far back from a chord of length W it just fills the horizontal FOV.

    p = W / (2 tan(fov_h/2)). The number that decides WHICH LENS took bar J: an
    embayment's headland-to-headland chord fills a portrait 1x frame only from
    0.93 W back, and a portrait 0.5x frame from 0.50 W. A viewpoint on the bay's
    own rim is not 0.93 W back from its own chord."""
    return W / (2.0 * math.tan(0.5 * fov_h))


def select_lens(hfov_needed, aspect=STILL_ASPECT):
    """The LONGEST of the phone's four lenses that still covers `hfov_needed`.

    Longest rather than shortest: a photographer reaching for 0.5x has given up
    resolution and does it only when 1x will not fit the subject, so the rule is
    'the tightest lens that fits', which is what a person does.

    WHEN NOTHING FITS IT RETURNS THE WIDEST WITH `covers` FALSE, and that case
    is not a failure of the function -- it is evidence. The widest lens on this
    phone is 89.91 deg across in portrait, and a bay seen from exactly half a
    chord back subtends 90.00 deg, so a standoff under 0.5002 chords CANNOT
    have produced bar J's frame with this instrument. The near-miss is a
    quantitative bound on where the photographer stood, recovered from nothing
    but the frame's content and the phone's spec sheet.
    """
    best = None
    widest = None
    for f, name in LENSES:
        _, h = portrait_fov(f, aspect)
        if widest is None or h > widest[2]:
            widest = (f, name, h, False)
        if h >= hfov_needed and (best is None or f > best[0]):
            best = (f, name, h, True)
    return best if best is not None else widest


def min_standoff_over_chord(aspect=STILL_ASPECT):
    """The closest a photographer can stand to a chord and still fit it in.

    The widest lens sets it: p/W = 1/(2 tan(h_max/2)). Anything nearer is
    excluded by the instrument, whatever the bay's size."""
    hmax = max(portrait_fov(f, aspect)[1] for f, _ in LENSES)
    return standoff_for_chord(1.0, hmax)


# ======================================================= the two frames, inferred
# WHAT FOLLOWS IS THE BAR'S OWN PROSE TURNED INTO NUMBERS, and each constant
# carries the sentence it came from and an interval. These are the ONLY inputs
# to the inference that are not geometry, and they are the only place a reader
# should argue with it.

# --- J. "the whole embayment from the cliff. Headland to headland, cliff
#     behind, a curved sand beach, and the surf running in multiple lines that
#     follow the curve all the way round" ... "Three to four separated breaking
#     lines across the wider parts" ... "It is a DISTANT frame."
J_CONTENT = dict(
    upright=True,
    # The embayment must fit headland to headland WITH the backing cliff. A
    # viewpoint on the bay's own rim stands within about half a chord of the
    # chord's midpoint -- it cannot be a full chord back, because the bay is
    # what it is standing on. `standoff_for_chord` turns that into a lens, and
    # THE CHORD CANCELS: the required FOV depends only on this ratio, so the
    # lens is inferred without knowing how big the bay is. That is the single
    # cleanest step in this file.
    standoff_over_chord=(0.35, 0.65),
    # Bar J and bar I1 both record SEPARATED lines with water between. The gap
    # between two breaking lines on a barred beach is the trough, and this
    # scene's own transform is what says how wide -- passed in, not declared.
    # The demand is that the gap be resolved in the print, which for a 4032-row
    # upright frame at 0.5x is ~38 px/deg.
    separation_px=(5.0, 20.0),
    frame_rows=4032.0,
    eye_above_ground=(1.45, 1.75),
    # An overview seascape puts the horizon in the upper third. Widened to a
    # fifth-to-two-fifths because the frame also has to hold the sky the bar
    # does not mention and the cliff it does.
    horizon_fraction=(0.20, 0.42),
)

# --- K. "Upright, from the cliff: a long crescent beach curving away to a
#     headland and a village, dune vegetation in the foreground, and the whole
#     open sea with the sun's glitter path running from the horizon into the
#     near field."
K_CONTENT = dict(
    upright=True,
    standoff_over_chord=(0.35, 0.65),
    # K2: "a long crescent with multiple shore-parallel surf lines, confirming
    # section J". Same demand, same instrument.
    separation_px=(5.0, 20.0),
    frame_rows=4032.0,
    # "dune vegetation in the FOREGROUND" -- plants at the eye's own ground
    # level, within a few metres to a few tens of metres. This is what pins the
    # BOTTOM edge of the frame, and with it the depression.
    foreground_range=(3.0, 40.0),
    eye_above_ground=(1.45, 1.75),
    horizon_fraction=(0.18, 0.40),
)


def _mid(iv):
    return 0.5 * (iv[0] + iv[1])


def infer_lens(standoff_over_chord=(0.35, 0.65), aspect=STILL_ASPECT):
    """Which of the four lenses can hold a bay seen from its own rim.

    THE CHORD CANCELS. A chord W seen from a perpendicular standoff p subtends
    2 atan(W/2p), and p is expressed as a multiple of W, so the required FOV is
    a function of the RATIO alone and the bay's size never enters. That is why
    this inference survives having no photograph and no map: it needs only the
    fact that the photographer was standing on the bay's own rim.

    Returns one record per end of the standoff interval and one for its middle.
    """
    out = []
    for r in (standoff_over_chord[0], _mid(standoff_over_chord),
              standoff_over_chord[1]):
        need = 2.0 * math.atan(1.0 / (2.0 * r))
        out.append(dict(standoff_over_chord=r, hfov_needed=need,
                        lens=select_lens(need, aspect)))
    return out


def infer_eye_height(D, s, content, aspect=STILL_ASPECT, f_mm=13.0):
    """The eye height the RESOLVED surf lines demand, with its interval.

    D  range from the eye to the outer breaking line (m)
    s  cross-shore spacing of two breaking lines (m) -- from the wave field
    """
    fov_v, _ = portrait_fov(f_mm, aspect)
    px_per_rad = content['frame_rows'] / fov_v
    lo_px, hi_px = content['separation_px']
    z_lo = eye_height_for_separation(D, s, lo_px / px_per_rad)
    z_hi = eye_height_for_separation(D, s, hi_px / px_per_rad)
    d_max, z_star = separation_ceiling(D, s)
    return dict(z_lo=z_lo, z_hi=z_hi, D=D, s=s, fov_v=fov_v,
                px_per_deg=px_per_rad * math.pi / 180.0,
                sep_max=d_max, z_star=z_star,
                demand_lo=lo_px / px_per_rad, demand_hi=hi_px / px_per_rad)


def infer_depression(content, fov_v, z):
    """The depression, bracketed three ways, and the bracket's midpoint.

    (1) THE HORIZON MUST BE IN FRAME. That alone gives delta < fov_v/2.
    (2) THE NAMED FOREGROUND MUST BE IN FRAME. The bottom edge strikes the
        photographer's own ground at range x, so delta > atan(h_eye/x) - fov_v/2
        -- and for a 106.6 deg upright frame from a standing eye this is
        NEGATIVE for any x beyond about 1.2 m, i.e. NOT BINDING. Recorded
        because a bound that does not bind is a real result: an ultrawide held
        level already contains the photographer's feet, so 'vegetation in the
        foreground' does not tell us the camera was tilted down.
    (3) WHERE THE HORIZON SITS. The only bound with any strength, and it is a
        read off an image this file does not have. It is carried as an interval
        and it dominates the result.
    """
    half = 0.5 * fov_v
    hi_horizon = half - math.radians(2.0)      # keep 2 deg of sky above it
    fg = content.get('foreground_range')
    lo_fg = -math.inf
    if fg is not None:
        h_eye = _mid(content['eye_above_ground'])
        lo_fg = math.atan(h_eye / fg[1]) - half
    f_lo, f_hi = content['horizon_fraction']
    d_from_f_lo = depression_from_horizon_fraction(f_lo, fov_v, z)
    d_from_f_hi = depression_from_horizon_fraction(f_hi, fov_v, z)
    lo = max(lo_fg, min(d_from_f_lo, d_from_f_hi))
    hi = min(hi_horizon, max(d_from_f_lo, d_from_f_hi))
    return dict(lo=lo, hi=hi, mid=0.5 * (lo + hi), half_width=0.5 * (hi - lo),
                bound_horizon_in_frame=hi_horizon, bound_foreground=lo_fg,
                from_fraction=(d_from_f_lo, d_from_f_hi))


def flat_sea_error(z, far, refraction=True):
    """What `beach_render.trace`'s FLAT sea plane costs, in angle.

    The plane at z = 0 runs to `far` and has no horizon: its farthest visible
    row is at depression atan(z/far). The real horizon is at `horizon_dip`. The
    render therefore paints sea over a band of sky `dip - atan(z/far)` tall, and
    everything between the true horizon and `far` is fictitious ocean.

    Returned in radians AND as a fraction of the frame, because the answer is
    that it is about one pixel and the ranking of a defect is the deliverable."""
    dip = horizon_dip(z, refraction)
    edge = math.atan(z / float(far))
    return dict(dip=dip, plane_edge=edge, over_paint=dip - edge,
                horizon_range=horizon_range(z, refraction),
                fictitious_range=float(far) - horizon_range(z, refraction))


def aerial_optical_depth(beta, path):
    """tau = beta * path, and the direct transmittance exp(-tau).

    Split out so the suite can guard the two numbers separately: the CHAIN is
    Koschmieder's V = 3.912/beta for the extinction coefficient, and the frame's
    own geometry for the path."""
    tau = float(beta) * float(path)
    return dict(tau=tau, T=math.exp(-tau))


def koschmieder_beta(visibility_m, contrast=0.02):
    """Extinction coefficient from meteorological visibility.

    V = -ln(eps)/beta with eps = 0.02 the standard contrast threshold, so
    beta = 3.912/V. Cited (Koschmieder 1924), not derived here."""
    return -math.log(contrast) / float(visibility_m)


def infer_frame(name, content, z_landform, D_lines, s_lines,
                aspect=STILL_ASPECT):
    """The whole camera for one of the owner's frames, with its intervals.

    `z_landform` is the eye height the SCENE can actually supply (the cliff brow
    the bed puts under the photographer plus a standing eye). `D_lines` and
    `s_lines` are the range to and the cross-shore spacing of the surf lines
    THIS SCENE's own transform produces -- both passed in, neither declared
    here, so the eye-height demand is a statement about the frame and this bed
    together rather than about a bay nobody has measured.
    """
    # THE INSTRUMENT TIGHTENS THE STANDOFF BEFORE THE STANDOFF CHOOSES THE
    # LENS, and that ordering is the finding: the widest lens on this phone
    # cannot hold a chord from nearer than `min_standoff_over_chord`, so the
    # lower part of the content interval is EXCLUDED rather than averaged over.
    p_min = min_standoff_over_chord(aspect)
    lo, hi = content['standoff_over_chord']
    standoff = (max(lo, p_min), max(hi, p_min * 1.0000001))
    lens_rows = infer_lens(standoff, aspect)
    f_mm = lens_rows[1]['lens'][0]
    fov_v, fov_h = portrait_fov(f_mm, aspect)
    dep = infer_depression(content, fov_v, z_landform)
    eye = infer_eye_height(D_lines, s_lines, content, aspect, f_mm)
    edges = frame_edges(z_landform, dep['mid'], fov_v)
    return dict(name=name, lens_rows=lens_rows, f_mm=f_mm, fov_v=fov_v,
                standoff=standoff, standoff_declared=(lo, hi),
                standoff_min=p_min,
                fov_h=fov_h, dep=dep, eye=eye, edges=edges,
                z_landform=z_landform,
                dip=horizon_dip(z_landform),
                horizon_range=horizon_range(z_landform),
                f_h=horizon_fraction(dep['mid'], fov_v, z_landform),
                # the alternative lens, kept because the selection is the one
                # step a reader is most likely to want to argue with
                alt_f_mm=lens_rows[0]['lens'][0],
                alt_fov=portrait_fov(lens_rows[0]['lens'][0], aspect))


def report(inferences=(), prn=print):
    """The whole inference, printed, in the run that draws the frames."""
    d = math.degrees
    prn('THE CAMERA IS AN INFERENCE, AND THIS IS THE INFERENCE '
        '(beach_camera.py).')
    prn('  There is no EXIF and no photograph in this repository. The input is')
    prn('  the bar\'s frozen inventory of what is in each frame; every number')
    prn('  below is an angle or a length, never a level (standing ruling).')
    prn('  THE INSTRUMENT: iPhone 16 Pro, four fixed 35-mm-equivalent focal')
    prn('  lengths, 4:3 stills, and bar J and K both record the frame UPRIGHT.')
    prn('  %-24s %7s %7s %7s   %s' % ('lens', 'diag', 'up-dn', 'l-r',
                                      'standoff/chord it needs'))
    for f, nm in LENSES:
        fv = equiv_fov(f)
        v, h = portrait_fov(f)
        prn('  %-24s %6.2f  %6.2f  %6.2f   %6.3f'
            % ('%g mm  %s' % (f, nm), d(fv['diag']), d(v), d(h),
               standoff_for_chord(1.0, h)))
    prn('  THE LENS IS CHOSEN BY A RATIO AND THE BAY\'S SIZE CANCELS: a chord')
    prn('  seen from p chords back subtends 2 atan(1/2p), so "the whole')
    prn('  embayment from its own rim" fixes the FOV without a map.')
    for inf in inferences:
        prn('')
        prn('  -- %s' % inf['name'])
        prn('     the content puts the photographer %.2f-%.2f chords back; the'
            % inf['standoff_declared'])
        prn('     INSTRUMENT excludes anything under %.4f chords (the widest'
            % inf['standoff_min'])
        prn('     lens is %.2f deg across upright and half a chord back needs'
            % d(max(portrait_fov(f)[1] for f, _ in LENSES)))
        prn('     90.00), so the interval used is %.4f-%.2f.' % inf['standoff'])
        for r in inf['lens_rows']:
            prn('     standoff %.3f chords -> needs %6.2f deg across -> %s'
                % (r['standoff_over_chord'], d(r['hfov_needed']),
                   '%g mm %s%s' % (r['lens'][0], r['lens'][1],
                                   '' if r['lens'][3] else '  (SHORT BY %.2f '
                                   'deg -- excluded)'
                                   % d(r['hfov_needed'] - r['lens'][2]))))
        prn('     LENS      %g mm, upright %.2f deg tall x %.2f wide'
            % (inf['f_mm'], d(inf['fov_v']), d(inf['fov_h'])))
        dp = inf['dep']
        prn('     DEPRESSION %.2f deg, bracket %.2f .. %.2f (+/- %.2f)'
            % (d(dp['mid']), d(dp['lo']), d(dp['hi']), d(dp['half_width'])))
        prn('       bound "horizon in frame with 2 deg of sky"  delta < %.2f'
            % d(dp['bound_horizon_in_frame']))
        prn('       bound "the named foreground is in frame"    delta > %.2f'
            % d(dp['bound_foreground']))
        prn('       -> the foreground bound DOES NOT BIND: an upright %.0f deg'
            % d(inf['fov_v']))
        prn('          frame held level already contains the ground at the')
        prn('          photographer\'s feet, so "vegetation in the foreground"')
        prn('          does not prove the camera was tilted down at all.')
        prn('       the horizon fraction is the only bound with strength and it')
        prn('       is a READ off an image this file does not have. ONE MEASURED')
        prn('       HORIZON ROW would collapse +/- %.2f deg to +/- 0.03 deg.'
            % d(dp['half_width']))
        ey = inf['eye']
        prn('     EYE HEIGHT is NOT measured by the dip: %.4f deg at %.1f m,'
            % (d(inf['dip']), inf['z_landform']))
        prn('       and only %.4f deg at 90 m -- a sixth of a degree between a'
            % d(horizon_dip(90.0)))
        prn('       low cliff and a high one, inside a hand-held tilt error.')
        prn('       WHAT DOES MEASURE IT is the resolved surf-line separation.')
        prn('       lines %.0f m apart at %.0f m, %.1f px/deg, resolved at '
            '%.0f-%.0f px' % (ey['s'], ey['D'], ey['px_per_deg'],
                              content_px(inf)[0], content_px(inf)[1]))
        prn('       -> demands an eye at %s .. %s m'
            % (_fmt_z(ey['z_lo']), _fmt_z(ey['z_hi'])))
        prn('       ceiling: no eye height can separate them by more than')
        prn('       %.3f deg, reached at z* = sqrt(D(D-s)) = %.0f m.'
            % (d(ey['sep_max']), ey['z_star']))
        prn('     THE LANDFORM SUPPLIES %.2f m, and that is where the frame is'
            % inf['z_landform'])
        prn('     drawn from. Horizon at %.1f%% of the frame from the top;'
            % (100.0 * inf['f_h']))
        prn('     top edge %.2f deg above the horizontal, bottom edge %.2f'
            % (-d(inf['edges']['top_angle']), d(inf['edges']['bot_angle'])))
        prn('     below it, striking the sea at %.1f m from the eye.'
            % inf['edges']['bot_range'])
    return None


def content_px(inf):
    return (inf['eye']['demand_lo'] * inf['eye']['px_per_deg'] * 180.0 / math.pi,
            inf['eye']['demand_hi'] * inf['eye']['px_per_deg'] * 180.0 / math.pi)


def _fmt_z(z):
    return 'unreachable' if z is None else '%.1f' % z


if __name__ == '__main__':
    report()
