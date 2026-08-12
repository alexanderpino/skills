"""
Swimming pool, 1.40 m deep -- physically-motivated render.

Chain (terrain-renderer/references/12-water-rendering.md):
  fetch-limited capillary-gravity wave field (no swell, no current)
   -> per-channel refraction of the sun; n_R != n_G != n_B  (dispersion)
   -> forward ray splat onto bed + 4 walls; folds emerge from ray density alone
   -> sun-disc penumbra blur, 0.53 deg compressed on entry by cos(ti)/(n cos(tt))
   -> sun visibility sampled AT THE SURFACE ENTRY POINT (shade sail), with penumbra
   -> Beer-Lambert over the light path, then again over the camera path
   -> liner albedo * transmittance   (b_b ~ 0: pool colour is the bottom, not scattering)
   -> ONE BOUNCE between bed and bed: total internal reflection off the underside
      of the surface, and a gather off the sunlit bed onto every vertical face --
      which is the whole of the light on a step riser seen from the anti-solar side
   -> the EXACT Fresnel equations at every water interface (not Schlick), with
      F0 from per-channel IOR (0.0197, not the 0.04 dielectric default)

Nothing in the caustic pattern is authored: no texture, no Voronoi, no noise.
The chromatic fringing on the bed is emergent -- three IORs, three fold sets.
"""
import numpy as np
from PIL import Image

# --------------------------------------------------------------------------- config
DEPTH = 1.40   # the DEEPEST point only. Depth is a field -- bed_depth(x, y) --
               # and every optical path length is taken from it. What is left of
               # this constant is the floor of the containing box, the extent of
               # the wall maps, and the deepest-case numbers in the diagnostics.
X0, X1, Y0, Y1 = 0.0, 8.0, 0.0, 4.0
W, H = 2400, 3600          # rendered at SSx, averaged down: glints are rare
SS = 3                     # events, and the waterline is a high-contrast edge
                           # portrait: the frame runs from the coping at the
                           # photographer's feet to the far coping, all water
RAY_NX, RAY_NY = 8192, 4096          # 33.5 M forward rays per channel
CAU_NX, CAU_NY = 2666, 1333          # 3 mm bed texels
WNU, WNV = 1800, 340                 # wall caustic maps
SHADOW_N = (2200, 1100)

IOR = np.array([1.3320, 1.3348, 1.3400])     # 620 / 545 / 460 nm
LAM = np.array([0.620, 0.545, 0.460])        # the wavelengths those three ARE, um
# Pure-water absorption, m^-1. PURE water -- Pope & Fry (1997), Appl. Opt.
# 36(33) 8710-8723, the integrating-cavity measurement that is the modern
# standard and the one this project's own bibliography names.
#
# THESE ARE BAND MEANS, NOT POINT SAMPLES, and that is a decision, not an
# accident. `a(lambda)` at the three nominal wavelengths is (0.2755, 0.0511,
# 0.00979); averaged over the Voronoi bands defined thirty lines below --
# 582.5-657.5, 502.5-582.5, 417.5-502.5 nm, which is what a channel of this
# renderer actually integrates -- the same table gives
#
#     a_band = (0.26170, 0.052988, 0.010224) m^-1
#
# The file's own doctrine two paragraphs down is that *a channel is a BAND, not
# a wavelength*; the bands tile 417.5-657.5 with no gap and no overlap, and every
# other spectral quantity here (n, the caustic eta, the dispersion sweep) is
# already sampled through them. Taking `a` at a delta function while everything
# beside it is taken over a band is the inconsistency, and `a` is the quantity
# where it costs most: it is strongly curved across the red band (0.0896 at
# 580 nm to 0.3400 at 650), so the point value and the band mean differ by 5.0%
# there. The band reading is the one this file's own model asks for. (A band mean
# of `a` is still an approximation -- Beer-Lambert over a band is the log of a
# mean of exponentials, not the mean of the exponents -- but it is first-order
# right where the point sample is not even that.)
#
# WHAT WAS WRONG BEFORE: (0.2750, 0.0546, 0.0145). Red was Pope & Fry at 620 nm
# to 0.2%; green was 6.9% high; and blue was 0.0145, which is Smith & Baker
# (1981) at 450 nm EXACTLY -- 48% above Pope & Fry, the wrong paper at the wrong
# wavelength, in a project whose own provenance file bans Smith & Baker for blue
# by name (that era's blue is contaminated by scattering in natural water).
# Two independent passes reached the same identification. `validate.py` tier 2
# checks this triple against both tables, point-sampled and band-integrated.
ABS = np.array([0.2617, 0.05299, 0.01022])
F0 = ((IOR - 1.0) / (IOR + 1.0)) ** 2


# --- Fresnel, exactly, because this is a reference ---------------------------
# The unpolarised reflectance of a smooth dielectric interface, from the Fresnel
# equations themselves. With sin t = sin i / n (Snell),
#
#     R_s = ((cos i - n cos t)/(cos i + n cos t))^2      # E perpendicular
#     R_p = ((n cos i -   cos t)/(n cos i +   cos t))^2  # E in the plane
#     R   = (R_s + R_p)/2                                # unpolarised sunlight
#
# THIS FILE USED TO SHIP SCHLICK (1994), `F0 + (1-F0)(1-cos i)^5`, everywhere.
# Schlick's whole justification is that it is one multiply-add cheaper than the
# square roots above; its error is quoted as ~1% of R for common dielectrics and
# for water it is nothing of the sort. Measured against the exact equations:
#
#     worst absolute, 0-90 deg   exact 0.5163 against Schlick 0.5751 at 83.8 deg
#     over the frame's own incidence range (38-79 deg, render.py's own
#       measurement of what this camera spans), Schlick / exact - 1 runs
#           -22.8%  at 51.3 deg   (exact 0.0360 against Schlick 0.0278)
#           +14.3%  at 79.0 deg   (exact 0.3152 against Schlick 0.3604)
#       crossing zero at 67.1 deg
#
# AND THAT SIGN FLIP IS THE POINT. It is not a grazing-only overshoot that a
# scale could absorb: inside one frame the fit is a fifth low on the mid water
# and a seventh high on the far water, so the far band read too much like a
# mirror while the mid band read too little, with no single multiplier able to
# fix both. The far water's specular term is the brightest thing in the picture
# and the mid water is most of its area, so the error sits on exactly the pixels
# a reflection model is judged by, in both directions at once. An
# approximation whose only argument is speed does not belong in a file whose only
# argument is being right. The exact form costs one sqrt and one divide per
# channel, measured at +1.1% of a full render (5m23s -> 5m27s at this resolution),
# and that is the entire price of the 14%.
#
# Provenance: Born & Wolf, *Principles of Optics*, §1.5.2 (the Fresnel
# coefficients); Schlick, *Computer Graphics Forum* 13(3) 233-246 (1994) for what
# was replaced. Guarded in `validate.py` by three things that do not go through
# the same expression: R(0) = F0, the Brewster identity R(atan n) = ((n^2-1)/
# (n^2+1))^2 / 2 exactly (a closed-form NUMBER -- Schlick misses it by 22%), and
# R_s >= R >= R_p over the whole range.
def fresnel(cos_i):
    """Exact unpolarised Fresnel reflectance, per channel. Returns (..., 3)."""
    ci = np.clip(np.asarray(cos_i, float), 0.0, 1.0)[..., None]
    ct = np.sqrt(np.maximum(1.0 - (1.0 - ci * ci) / IOR ** 2, 0.0))
    rs = ((ci - IOR * ct) / (ci + IOR * ct)) ** 2
    rp = ((IOR * ci - ct) / (IOR * ci + ct)) ** 2
    return 0.5 * (rs + rp)


# --- a camera channel is a BAND, not a wavelength ----------------------------
# The three IORs above are three delta functions standing in for three broad
# sensor bands, and a 3-point quadrature is only as good as the integrand is
# smooth over the sample spacing. On a caustic FOLD the integrand is smooth over
# the dispersion scale and three samples are plenty -- that is why the fringing
# on the folds reads correctly. On an OPAQUE SILHOUETTE the integrand is a step
# AT the dispersion scale, and three deltas resolve a step as a comb: three
# separately-placed edges, so the pixel between them carries one primary with
# the other two missing. That is not dispersion, it is aliasing of dispersion,
# and it is what put saturated blue and yellow speckle on every step nosing.
# MEASURED before the fix: the red and blue images of the bed are separated by
# 9.8 mm on the floor and 8.7 mm at the step unit, which is 2.1 and 2.4 OUTPUT
# pixels -- and 0.33% of all water rays disagreed about WHICH surface they hit.
#
# n(lambda) is not a new constant: a two-parameter Cauchy fit through the three
# (lambda, n) pairs already in the file reproduces all three to 5e-5, so the
# three IORs were themselves drawn from one dispersion curve and the curve can
# be recovered from them.
_uu2 = 1.0 / LAM ** 2
CAUCHY_B = (((_uu2 - _uu2.mean()) * (IOR - IOR.mean())).sum()
            / ((_uu2 - _uu2.mean()) ** 2).sum())
CAUCHY_A = IOR.mean() - CAUCHY_B * _uu2.mean()


def n_water(lam_um):
    """Refractive index at a wavelength, from the file's own three IORs."""
    return CAUCHY_A + CAUCHY_B / np.asarray(lam_um) ** 2


# The bands are the VORONOI CELLS of the three nominal wavelengths: edges at the
# midpoints 582.5 and 502.5 nm, the outer edges mirrored so each band is centred
# on its nominal. They then tile 417.5-657.5 nm with no gap and no overlap,
# which is the minimum a three-channel sensor must do to reproduce a continuous
# spectrum without holes. No new number enters -- only the three wavelengths
# that were already here. A real Bayer CFA overlaps its neighbours instead of
# tiling them (`?`), which would smear the edge slightly MORE than this, so the
# tiling choice is the conservative one.
_mid = 0.5 * (LAM[:-1] + LAM[1:])
BAND = np.array([[_mid[0], 2 * LAM[0] - _mid[0]],
                 [_mid[1], _mid[0]],
                 [2 * LAM[2] - _mid[1], _mid[1]]])       # [lo, hi] um, per channel
print("dispersion: n(lam) = %.5f + %.6f/lam[um]^2, max residual on the three "
      "stated IORs %.1e" % (CAUCHY_A, CAUCHY_B, np.abs(n_water(LAM) - IOR).max()))
print("  channel bands (nm): " + "  ".join(
    "%s %.0f-%.0f  dn %.5f" % (nm, 1000 * b[0], 1000 * b[1],
                               n_water(b[0]) - n_water(b[1]))
    for nm, b in zip("RGB", BAND)))

# NOAA solar position, Aljezur 37.319N 8.803W, 2026-08-10 18:41 WEST:
#   elevation 21.02 deg, azimuth 273.75 deg (due west), air mass 2.77
SUN_DIR = np.array([-0.93141, 0.06104, 0.35878])   # +x east, +y north, +z up
SUN_DIR /= np.linalg.norm(SUN_DIR)
SUN_COL = np.array([1.000, 0.892, 0.674]) * 8.6   # golden: AM 2.77, not a noon sun
SKY_TOP = np.array([0.26, 0.46, 0.98])
SKY_HOR = np.array([0.86, 0.90, 0.98])
SKY_AMB = np.array([0.26, 0.42, 0.66]) * 2.15   # clear sky is still a big blue source
# ...but SKY_AMB is the sky the WATER sees: through the Snell window it is
# zenith-weighted, and the zenith is the blue part. A horizontal stone surface
# sees a cosine-weighted hemisphere instead, and at a 21 degree sun most of that
# hemisphere's energy is in the aureole and the horizon band around the sun,
# reddened by the same air mass 2.77 that makes SUN_COL golden. Feeding the
# water's blue ambient to the stone is what made the deck come out neutral grey
# in the previous frame: a warm albedo times a blue illuminant is grey.
SKY_DECK = SKY_AMB * 0.30 + SUN_COL * 0.075
SAIL_TAU = 0.30          # shade fabric transmits ~15-20%, DIFFUSELY:
                         # it lifts the shadow without making caustics

# --- camera -----------------------------------------------------------------
# The reference is a CLOSE-UP over the water: the frame is water, the pool edge
# is a border at the top, and there is no garden in it. Two constraints fix the
# viewpoint and neither is free:
#   * the specular path.  A facet reflects the sun to the camera when its normal
#     bisects L and V.  With the sun at 21 deg and the camera due east of the
#     target, |theta_v - 21| < 12 deg keeps the required slope inside the field's
#     rms (0.058 far, 0.123 over the jet) -- that is the ONLY band in which
#     spec C's isolated glints can exist.  Look down at 60 deg and there is no
#     sparkle anywhere, at any roughness.
#     WHERE the sparkle can sit is NOT the mirror band, and the previous note
#     here had it exactly backwards. It said: the mean surface mirrors the sun
#     at theta_v = 21 deg, a ground distance 2.607 h, so put that on the jet and
#     you need a 3.57 m eye. But at the mirror point the required facet slope is
#     ZERO, and a glassy surface reflects the sun's disc better than a rough one
#     does -- the contrast between rough patch and calm water there is
#     (s_calm/s_jet)^2 < 1, i.e. the jet would be the DARKER of the two. What
#     lives at the mirror band is precisely the broad shimmering road spec C
#     rules out, which is why this frame has one.
#     Spec C's "compact patch of isolated points on otherwise glassy water" is
#     the opposite regime: the required slope has to be far enough out on the
#     calm water's slope distribution that the calm water cannot reach it, and
#     still inside the rough patch's. That is a WINDOW in required slope, and
#     the diagnostic further down measures both ends of it off the field itself
#     (r* where the contrast crosses 1, and the r for 10x and 100x). It puts
#     |theta_v - 21 deg| at roughly 16-19 deg, so the eye sits about 1.2 of its
#     own heights out from the glint on the steep branch, or 12-30 on the
#     grazing one -- NOT 2.6, and not 4.8 m from a 1.85 m eye.
#     That changes the verdict's SHAPE. The steep branch says a poolside eye can
#     hold a compact sparkle patch about 2 m in front of it. The obstruction is
#     that all specular structure lies on ONE line in plan -- the sun's azimuth
#     through the eye, which at azimuth 273.75 deg is due west at constant y --
#     so the eye must sit within ~0.5 m of the glint's y and 1.2 h east of it.
#     The jet is at (0.10, 1.15): the eye that lights it is at about (2.8, 1.3),
#     which is over the water. Sweeping every deck closes it: the east deck is
#     the only one whose westward line lies over water at all, and from x >= 8.4
#     the jet is 7.5 m away, needing h = 6.4 m (steep) or h <= 0.75 m (grazing,
#     and then the mirror road lands in the near foreground instead). So spec C
#     is still unreachable for THIS jet -- but the miss is 1.9 m of camera, not
#     1.7 m of camera height, and the fix names itself: a return fitting whose
#     boil lands in the glint window the diagnostic prints. For this eye that
#     window is on the water at x ~ 7, y ~ 2 -- a return in the EAST wall, which
#     is where the plant room of a pool photographed from the east deck usually
#     puts it. That is a scene-layout statement for field.py, with the target
#     printed in world coordinates rather than argued for.
#   * the caustic net.  25-40 cells at 15-30 cm needs 4-8 m of water in frame.
#   * the waterline has to be legible somewhere.  At the FAR coping it is four
#     pixels of stone; the only place a pool edge can be read is the one under
#     the photographer, so the bottom of the frame is put on it at 1.2 m.
# Phone at chest height on the east deck, a metre back from the edge, 34 deg
# down, portrait: bottom edge on the near coping (theta_v 57 deg), top edge at
# theta_v 11 deg and 9.5 m out, 8 m of ground in between -- all of it water
# before the yaw below, two thirds of it after. The mirror direction
# for a 21 deg sun used to cross that span a fifth of the way down; since the
# yaw below it crosses 1.13 half-widths outside the left edge instead, which is
# the whole point of the yaw.
#
# The lateral position moved 0.40 m north an earlier round, to the pool's own
# centre line, and that is what first put the step unit -- set into the north
# wall at mid-length rather than 8 m away in the far corner -- inside the
# 15.8 deg half-width of the frame. EYE has not moved since, and does not move
# here: it is the wave-4 arbitration's, and every specular number in this file
# is a function of it. Only the AIM changes below.
EYE = np.array([9.40, 1.95, 1.85])    # east: the eye STANDS on the anti-solar side
#
# --- TWO AZIMUTH CONVENTIONS, AND THE DEFECT THAT LIVED BETWEEN THEM ----------
# STATE THIS BEFORE USING ANY BEARING IN THIS FILE, because six waves passed
# with a camera pointed at the sun and nobody saw it:
#
#   * CAM_AZ, and every bearing computed here with atan2(y, x), is the MATH
#     convention -- radians CCW from +x, and +x is EAST, +y NORTH. Due west is
#     180 deg, north is 90 deg.
#   * the bar's solar azimuth, 273.75 deg, is the COMPASS convention -- degrees
#     CW from north. Due west is 270 deg.
#   * they convert as   math = 90 - compass  (mod 360),   compass = 90 - math.
#
# So the sun's plan bearing IN THIS FILE'S CONVENTION is 90 - 273.75 = 176.25
# deg, which is what atan2(SUN_DIR[1], SUN_DIR[0]) returns, and the old
# CAM_AZ = 176.6 deg was 0.35 deg from it, NOT the 97 deg that reading 176.6
# against 273.75 in one convention suggests. That near-identity is exactly what
# a reader skimming two numbers in two conventions cannot see, and it is how
# "anti-solar to 0.4 deg" -- true of where the eye STANDS, false of where it
# LOOKS -- survived six waves on this line.
#
# --- WHERE THE CAMERA POINTS NOW ---------------------------------------------
# The bar was written from a photograph taken 18.75 deg off the sun's bearing,
# and that offset is the only thing about the aim that section C is a statement
# about. It is reproduced here EXACTLY, in this file's convention:
#
#       CAM_AZ = 176.25 - 18.75 = 157.50 deg    (compass 292.5 deg)
#
# THE MAGNITUDE IS THE MEASUREMENT AND THE SIGN IS THE SCENE'S. What the
# reference fixes is the angle between the aim and the sun; it does not fix the
# pool's own bearing relative to north, which was never measured and which is
# what would decide the handedness. In THIS basin the sign is decided by the two
# frame-critical features, and they decide it unanimously:
#   * turning the aim 18.75 deg the other way (CAM_AZ 195 deg) takes the step
#     unit -- north wall, mid-length, two waves in the placing -- to 0% in
#     frame, measured on its own nosing arcs. It is the one feature that makes
#     refraction legible and it cannot be re-placed from here.
#   * turning it this way takes 96.5% of those nosings into frame (57.2% before)
#     and takes the sail's shadow out, and the sail is an occluder whose ONLY
#     constraint is that its shadow edge be in frame (bar section E). One of the
#     two is movable at zero physical cost and the other is not.
# Equivalently: this basin's long axis runs at compass 292.5 rather than 255,
# i.e. the scene is the reference geometry mirrored about the sun's bearing.
# Every quantity section C prices -- the offset angle, the required facet slope,
# the reachability -- is invariant under that mirror.
#
# --- WHAT A YAW DOES AND DOES NOT MOVE ---------------------------------------
# It moves NOTHING in the world. The specular condition at a surface point is
# that the facet normal bisect L and V, and V is fixed by the point and by EYE;
# CAM_AZ appears nowhere in it. So the sun's specular line still runs from EYE
# along the sun's plan bearing, r = 0 still lands at (4.60, 2.26), and the jet's
# boil is still 0.25 deg off that line and still inside the >=10x glint window.
# A yaw is a statement about the FRAME, and what it buys is which of those the
# frame contains: the mirror band sits 4.81 m out, where the line is 18.75 deg
# off the aim and the frame is +-15.8 deg wide, so the road leaves the picture;
# the glint window sits 1.4-2.5 m out, where the down-tilt widens the frame's
# azimuthal reach to about +-20.3 deg, so it stays. That 1.4-2.5 m against
# 3.5-7.2 m separation is the whole of what makes the fix possible, and it is a
# property of THIS eye height and THIS sun elevation, not a general one.
# THE PRICE, stated rather than discovered later: the frame no longer runs down
# the pool's long axis, so it falls from 88.3% water to 66.0%, with 16.9% of it
# north terrace. The composition-preserving alternative is to rotate the BASIN
# by 18.75 deg instead -- same optics, water-filled frame -- but that is a
# statement about the sun's bearing in scene coordinates, and it would carry the
# glint window off the return fitting, which is field.py's and frozen.
CAM_AZ = np.deg2rad(157.50)
CAM_EL = np.deg2rad(-33.35)
FOV = np.deg2rad(46.0)
TGT = EYE + 7.0 * np.array([np.cos(CAM_AZ) * np.cos(CAM_EL),
                            np.sin(CAM_AZ) * np.cos(CAM_EL), np.sin(CAM_EL)])
# The sail follows the frame, as it did when the eye moved 0.40 m north and it
# moved 0.70 m with it. Same quad, same heights, same shape: +1.50 m in y, which
# is a TRANSLATION and not a reshaping. It is the whole of what the yaw above
# costs elsewhere in the file, and it is not a free choice of composition --
# section E keeps this object only as an occluder, and its one stated
# requirement is that its shadow EDGE fall on water that is in shot. After the
# yaw its shadow at the old y left the picture entirely (0% of the shadow edge
# that lies on water was in frame, against 83.5% before), so the sail moves the
# amount that puts the same SHARE of the visible water in shade as before:
# 16.5% before the yaw, 17.1% after, with the shadow quad still landing wholly
# inside the basin (its far corner reaches y = 3.70 against a wall at 4.00).
# The shadow still clears the step unit and the section C glint window, so
# neither the refraction test nor the sparkle test is shaded by it.
SAIL = np.array([[-5.10, 1.30, 2.72], [-2.10, 1.70, 2.55],
                 [-2.40, 4.10, 2.35], [-5.40, 3.70, 2.55]])
EXPOSURE = 0.275      # the camera exposes for a 21-degree sun
# ...and the radiance at which one term ALONE whites out a pixel, solved out of
# the ACES constants in `encode` so it follows EXPOSURE if that moves. It is the
# unit the specular measurements below are quoted in, because "blown" is a
# statement about this curve and not about a taste.
_ys = ((250. / 255. + .055) / 1.055) ** 2.4
_qa, _qb, _qc = 2.51 - 2.43 * _ys, .03 - .59 * _ys, -.14 * _ys
L_WHITE = ((-_qb + np.sqrt(_qb ** 2 - 4 * _qa * _qc)) / (2 * _qa)) / EXPOSURE

# --- the pool edge, in section ----------------------------------------------
# Not a boolean rectangle.  A poured wall, a coping course bedded on it that
# OVERHANGS the wall face, and a bullnose rolled over that overhang.  Every
# number here is a dimension off a real coping stone, and each one does visible
# work: the overhang makes the undercut the water sits in, the bullnose makes
# the roll that catches or loses the sun depending on which side of the pool it
# is, and the freeboard makes the reflection of the coping in the water.
#
# --- THE FREEBOARD IS THE LINER'S, NOT THE STONE'S ---------------------------
# Bar section B2b, reported by the reference observer and therefore carrying
# A-F weight: "the edge of the pool should be a little higher. A blue side wall
# of about 10 cm, and then the stones."
#
# Read that as written and it fixes TWO numbers, not one, because the observer's
# 10 cm and the file's old 75 mm are not the same measurement:
#   * the observer's 10 cm is the height of the BLUE -- still water up to where
#     the built edge starts.
#   * the file's 75 mm was ZD, the coping TOP, which is a bullnose radius and a
#     bead higher than that, so the old blue band was 43 mm of STONE.
#
# A SIXTH REFERENCE PHOTOGRAPH, supplied mid-wave, shows that section in a
# corner of the wall from the deck, and it has THREE elements rather than two:
#     water | blue liner | a narrow GREY CONCRETE BEAD | sandstone coping
# The grey sliver is roughly a fifth of the blue's height and it is what the
# liner's bead track sits behind. It is not decoration: blue-straight-into-stone
# reads extruded, and a 20 mm grey line is what makes the edge read as built.
# So the section is stacked from the bottom up and ZD is the SUM rather than a
# number of its own:
#     FREEB 0.100  still water -> top of the blue     (the observer's 10 cm)
#     BEAD  0.020  the grey bead                      (`?` a fifth of the blue,
#                                                      a visual reading)
#     ZLIP  0.120  -> underside of the stone
#     ZD    0.152  -> coping top                      (was 0.075)
# `?` if the observer's "10 cm" was instead the whole freeboard to the top of
# the stone, ZD would be 0.100 and the blue about 50 mm; the reading taken here
# is the one that makes the sentence's own clause -- "about 10 cm, AND THEN the
# stones" -- a statement about the blue, and the sixth photograph's three-element
# section is what settles it, since the grey bead has to come from somewhere.
#
# In a liner pool the blue band IS the liner: the sheet runs up the wall to that
# bead track, so the colour above the water is the colour below it. It is shaded
# from LINER_TINT by `liner_band` below, not by `paving`, and `tiles` no longer
# carries a mosaic course under it.
BULR =  0.032     # bullnose radius
FREEB=  0.100     # the blue liner band: still water to the grey bead
BEAD =  0.020     # ? the grey concrete bead over it, a fifth of the blue
ZD   =  FREEB + BEAD + BULR   # coping top above the still waterline
ZG   = -0.030     # lawn, if it ever gets in frame -- it does not
SLIP = -0.020     # the coping overhangs the wall face by 20 mm, into the pool
SBUL = SLIP + BULR
ZCEN = ZD - BULR  # centre of the bullnose arc, in (s, z)
ZLIP = ZCEN       # lowest point of the bullnose == top of the BEAD
COPW =  0.34      # width of the coping course
WET  =  0.210     # how far back from the lip the stone is still splash-damp
# A real pool liner is BLUE, not white plaster. Absolute albedo ~ (0.24, 0.54, 0.70):
# reflective enough to stay bright, saturated enough to carry the colour itself.
LINER_TINT = np.array([0.30, 0.79, 0.92])

rng = np.random.default_rng(20260810)

# --------------------------------------------------------------------------- the plan
# ONE function owns the shape of the water in plan, and one owns the shape of
# the bed. Everything downstream -- the coping trace, the lip occluder, the wall
# shading, the meniscus, the caustic pass, the Beer-Lambert path -- consumes
# them rather than re-deriving the rectangle. Swapping a kidney-shaped boundary
# or a sloping shelf in is then a change to these two functions and nothing else.
#
# pool_sdf is the MITRED (max-norm) distance for the box instance, not the true
# Euclidean one: a coping course is laid with a mitre joint at the corner, so the
# max norm is the right metric for where the stones are, and the bullnose sweeps
# round the mitre exactly as a laid one does. The mitred form is still convex,
# which is what the camera-side edge march exploits below -- see POOL_CONVEX.
POOL_CONVEX = True          # true for the box; a kidney with a concave lobe is not


def pool_sdf(x, y):
    """Signed outward distance from the water's plan boundary; <0 inside."""
    return np.maximum(np.abs(x - .5 * (X0 + X1)) - .5 * (X1 - X0),
                      np.abs(y - .5 * (Y0 + Y1)) - .5 * (Y1 - Y0))


def pool_sdf_grad(x, y):
    """Outward unit gradient of pool_sdf, plus a flag saying which axis carries
    it (the coping course runs ALONG the boundary, so the caller needs to know)."""
    a = np.abs(x - .5 * (X0 + X1)) - .5 * (X1 - X0)
    b = np.abs(y - .5 * (Y0 + Y1)) - .5 * (Y1 - Y0)
    e = a >= b
    return (np.where(e, np.sign(x - .5 * (X0 + X1)), 0.),
            np.where(e, 0., np.sign(y - .5 * (Y0 + Y1))), e)


# --- the bed, as a field ------------------------------------------------------
# A RADIUS ENTRY STEP -- the "wedding cake" unit every vinyl-liner pool has --
# set into the north wall at mid-length, plus a bench lobe further west. Both are
# part of the LINER SHELL: same vinyl, same colour, continuous over the form.
# They are not a stone insert, and they are not decoration: they are the only
# straight-ish edges in the basin, and a circular nosing is the specific shape
# that a decorative wobble cannot fake. A wobbling straight line is a line with
# noise on it; a circular arc seen through a wavy interface stays a coherent arc
# whose local tangent swings, and only a real refracted view ray does that.
#
# Dimensions are a standard unit: tread 300 mm, riser 240/255 mm, three treads,
# 3.0 m along the wall and 1.5 m out into the water. The last drop to the floor
# is 700 mm -- that is what a three-tread unit in a 1.40 m basin actually does;
# you sit on it.
#
# WHERE IT SITS. Two constraints, and the previous placement satisfied only one.
#  * THE SUN, which is not a composition choice.  The refracted sun travels EAST
#    under water at 44.4 deg from vertical, so a tread that steps down toward the
#    east lies in its own nosing's shadow: 235 mm of a 300 mm tread. A flight
#    whose descent sweeps through east is 80% self-shadowed and shows no caustic
#    at all. Both of the west-wall corners descend eastward over half their
#    sweep. A unit centred on a side wall sweeps its descent through the whole
#    half-circle, so the self-shadow runs from 235 mm at the east end to 16 mm at
#    the south point -- a gradient that falls out of the geometry, and every
#    tread that faces the camera keeps a lit outer strip.
#  * THE FRAME, which the last placement lost.  At 7.5-9 m the flight is seen at
#    theta_v 11-14 deg: the treads foreshorten to 24% of their width, the whole
#    unit is 130 px of a 1200 px frame, the 12.9 mm nosing wobble projects to
#    0.6 px, and Fresnel on the surface above it is 0.25-0.36, which puts a
#    near-neutral sky reflection over everything the unit was built to show.
#    A 90 deg CORNER unit cannot be brought closer: from a viewpoint near its own
#    corner a 2.2 m quarter-arc subtends 40-60 deg of azimuth and leaves the
#    31.6 deg frame. A half-circle centred on the wall does not have that
#    problem -- its bulge points at the camera and its ends recede -- so at
#    x = 6.0 the outer nosing comes to 3.4 m, theta_v 28 deg, Fresnel 0.05, and
#    the arcs sweep 90 deg of frame instead of 15.
# The unit sits east of the mirror band (theta_v 21 deg, at 4.8 m) rather than
# under it, so the sun glitter road crosses OPEN water beyond the steps.
STEP_C = np.array([6.00, Y1])                     # the arcs are centred ON the wall
STEP_R = np.array([0.90, 1.20, 1.50])             # nosing radii, 300 mm treads
STEP_Z = np.array([-0.205, -0.445, -0.700])       # tread levels below still water
BENCH_C = np.array([3.00, 4.35])                  # the bench lobe: a disc cut by
BENCH_R = 0.85                                    # the north wall, so its leading
BENCH_Z = -0.445                                  # edge is an arc, at tread-2 level
NOSE_R = 0.025          # ? nosings are eased, not arrised -- 25 mm reads as the
                        # ? shading round-over only; it is under a pixel of silhouette


def bed_z(x, y):
    """Height of the bed under (x, y). The floor, the radius step, the bench."""
    r = np.sqrt((x - STEP_C[0]) ** 2 + (y - STEP_C[1]) ** 2)
    z = np.where(r <= STEP_R[0], STEP_Z[0],
                 np.where(r <= STEP_R[1], STEP_Z[1],
                          np.where(r <= STEP_R[2], STEP_Z[2], -DEPTH)))
    rb = np.sqrt((x - BENCH_C[0]) ** 2 + (y - BENCH_C[1]) ** 2)
    return np.where(rb <= BENCH_R, np.maximum(z, BENCH_Z), z)


def bed_depth(x, y):
    """Water depth over the bed at (x, y). DEPTH is now only the deepest point."""
    return -bed_z(x, y)


# The bed as a union of vertical cylinders {r <= R, z <= ztop}, which is exactly
# the staircase above: the union's upper surface is the deepest ztop whose disc
# contains the point. Analytic, so the caustic pass pays four quadratics and no
# march. (cx, cy, R, ztop)
CYL = [(STEP_C[0], STEP_C[1], STEP_R[0], STEP_Z[0]),
       (STEP_C[0], STEP_C[1], STEP_R[1], STEP_Z[1]),
       (STEP_C[0], STEP_C[1], STEP_R[2], STEP_Z[2]),
       (BENCH_C[0], BENCH_C[1], BENCH_R, BENCH_Z)]
# Bounding box of everything that is not the flat floor, in PLAN, so a ray whose
# whole horizontal run misses it can skip the cylinder tests entirely.
STEP_BB = (min(STEP_C[0] - STEP_R[2], BENCH_C[0] - BENCH_R),
           max(STEP_C[0] + STEP_R[2], BENCH_C[0] + BENCH_R),
           min(STEP_C[1] - STEP_R[2], BENCH_C[1] - BENCH_R),
           max(STEP_C[1] + STEP_R[2], BENCH_C[1] + BENCH_R))

# --------------------------------------------------------------------------- wave field
# Four bands. The structure is the room-acoustics one: EARLY reflections explicit
# and coherent, LATE reverberation statistical -- because after several bounces a
# basin field is diffuse, and a random-phase spectrum IS its correct description.
#   A  wind          short, incoherent, uniform, killed in the lee
#   B1 jet near      direct + first-order wall images: coherent arcs near the inlet
#   B2 reverb tail   the diffuse late field: random phase, near-ISOTROPIC directions
#                    (a reverberant basin has no preferred direction; a wind sea does)
#   C  jet boil      short waves at the outlet, e-folding ~2 m -> the local rough patch
NU = 1.004e-6

from field import (X0, X1, Y0, Y1, JET_XY, SIGMA_W, LAM_MIN, FP_SIGMA,
                   grad_grid, grad_points, slope_var_points, normal_from_grad,
                   jet_envelope, shelter, rms_slope, _norm_jets)

def refract(ix, iy, iz, nx, ny, nz, eta):
    """Snell's law as a direction map, WITH its total-internal-reflection branch.

    `eta` = n_incident / n_transmitted; `n` must oppose the incident ray. Writing
    the transmitted direction as `t = eta*i + f*n`, orthogonality of the tangential
    part to `n` and |t| = 1 give `f = eta*cos i - cos t` with

        k = cos^2 t = 1 - eta^2 (1 - cos^2 i)

    and k < 0 exactly when sin i > 1/eta -- the critical angle asin(1/eta), which
    exists only for eta > 1 (looking OUT of the denser medium). Past it there is
    no transmitted direction at all: every photon reflects, and the Fresnel R that
    goes with this same interface is 1 there, identically.

    THE BUG THIS FIXES. The old line clamped k at 0 and returned
    `eta*i + eta*cos(i)*n` regardless -- a vector of length `eta*sin i > 1` lying
    flat in the interface plane. Not a unit vector, not the TIR reflection, not a
    flag: a direction that does not exist, handed back silently. Nothing
    downstream could tell it from a real one, because nothing downstream measured
    its length. Unreachable from today's call sites (all five pass eta = 1/n < 1,
    air -> water, where k >= 1 - eta^2 >= 0), and squarely on the path of the
    underwater-camera pass the README describes, which is written entirely around
    this branch.

    THE CONTRACT. Past the critical angle this returns the NULL vector (0, 0, 0);
    `is_tir(t)` is the predicate. Zero was chosen over a NaN or a fourth return
    value because it keeps the signature, it propagates to zero radiance rather
    than to a poisoned frame, and it is checkable with one dot product -- which is
    what `validate.py` does. The five call sites below cannot reach the branch, so
    each declares which side of the interface it is on instead: an assert on eta
    where the eta is computed there, a comment where it is a literal 1/IOR. The
    onset of the null return is cross-checked in the suite against the angle at
    which the exact Fresnel R reaches 1, i.e. against different code.
    """
    cosi = -(ix * nx + iy * ny + iz * nz)
    k = 1.0 - eta * eta * (1.0 - cosi * cosi)
    f = eta * cosi - np.sqrt(np.maximum(k, 0.0))
    tx, ty, tz = eta * ix + f * nx, eta * iy + f * ny, eta * iz + f * nz
    # One reduction decides whether the branch was reached at all, so the eta < 1
    # call sites pay a min() over the batch and nothing else.
    if np.min(k) >= 0.0:
        return tx, ty, tz
    ok = k >= 0.0
    return tx * ok, ty * ok, tz * ok


def is_tir(tx, ty, tz):
    """True where `refract` returned its null vector. A transmitted direction is
    a unit vector, so |t|^2 is either 1 or 0 and the 0.5 threshold cannot be
    reached by round-off from either side."""
    return (tx * tx + ty * ty + tz * tz) < 0.5


BIG = np.float32(1e9)


def _cyl_entry(px, py, tx, ty, tz, pz=0.0):
    """Entry point of a downgoing ray into the UNION of the bed cylinders.
    Returns (t, is_riser, which). The union's first entry is the minimum of the
    per-solid entries, so no CSG walk is needed -- only four quadratics.
    `pz` is the ray's starting height; 0 (the still surface) for every caustic
    and camera ray, negative for the inter-reflection gather, which starts on a
    riser. It used to be hard-coded to 0 in the two places z enters."""
    n = px.shape
    bt = np.full(n, BIG); bf = np.zeros(n, bool); bi = np.full(n, -1, np.int8)
    a = tx * tx + ty * ty
    vert = a <= 1e-14
    inva = 1.0 / np.where(vert, 1.0, a)
    down = tz < -1e-9                             # z(t) <= ztop  <=>  t >= ztop/tz
    tzd = np.minimum(tz, -1e-9)
    for i, (cx, cy, R, ztop) in enumerate(CYL):
        ox, oy = px - cx, py - cy
        b = 2.0 * (ox * tx + oy * ty)
        c = ox * ox + oy * oy - R * R
        disc = b * b - 4.0 * a * c
        hit = (disc > 0.0) & ~vert
        sq = np.sqrt(np.where(hit, disc, 0.0))
        t1 = np.where(hit, (-b - sq) * 0.5 * inva, BIG)
        t2 = np.where(hit, (-b + sq) * 0.5 * inva, -BIG)
        t1 = np.where(vert, np.where(c < 0.0, -BIG, BIG), t1)
        t2 = np.where(vert, np.where(c < 0.0, BIG, -BIG), t2)
        tc = np.where(down, (ztop - pz) / tzd, BIG)
        tin = np.maximum(t1, tc)
        ok = (tin < t2) & (tin > 1e-6) & (tin < bt)
        bt = np.where(ok, tin, bt)
        bf = np.where(ok, t1 > tc, bf)            # entered through the round face
        bi = np.where(ok, i, bi)
    return bt, bf, bi


def scene_hit(px, py, tx, ty, tz, pz=0.0):
    """First hit of a downgoing ray in the pool, starting at height `pz`
    (0 = the still surface, which is where every caustic and camera ray starts).
    Surface ids:
         0 = a horizontal bed face -- floor, tread or bench top; (u,v) = (x,y)
         1..4 = the walls x0, x1, y0, y1;                        (u,v) = (along,z)
         5 = a cylindrical riser of the step unit;               (u,v) = (x,y)
    `cyl` says which cylinder a riser hit belongs to, so the caller can get the
    outward normal without a second intersection."""
    with np.errstate(divide='ignore', invalid='ignore'):
        s = np.stack([
            np.where(tz < -1e-9, (-DEPTH - pz) / tz, BIG),
            np.where(tx < -1e-9, (X0 - px) / tx, BIG),
            np.where(tx > 1e-9, (X1 - px) / tx, BIG),
            np.where(ty < -1e-9, (Y0 - py) / ty, BIG),
            np.where(ty > 1e-9, (Y1 - py) / ty, BIG)])
    s = np.where(np.isfinite(s), s, BIG)
    sid = np.argmin(s, 0).astype(np.int8)
    sm = np.take_along_axis(s, sid[None].astype(np.intp), 0)[0]
    cyl = np.full(px.shape, -1, np.int8)

    # Prune: a ray can only meet the step unit if its horizontal run crosses the
    # unit's plan bounding box. Everything else keeps the flat-floor fast path.
    L = np.minimum(sm, (DEPTH + pz) / np.maximum(-tz, 1e-9))
    ax, bx2 = px, px + tx * L
    ay, by2 = py, py + ty * L
    near = ((np.minimum(ax, bx2) <= STEP_BB[1]) & (np.maximum(ax, bx2) >= STEP_BB[0]) &
            (np.minimum(ay, by2) <= STEP_BB[3]) & (np.maximum(ay, by2) >= STEP_BB[2]))
    idx = np.flatnonzero(near)
    if idx.size:
        pzi = pz if np.ndim(pz) == 0 else pz[idx]
        ct, cf, ci = _cyl_entry(px[idx], py[idx], tx[idx], ty[idx], tz[idx], pzi)
        take = ct < sm[idx]
        j = idx[take]
        sm[j] = ct[take]
        sid[j] = np.where(cf[take], 5, 0).astype(np.int8)
        cyl[j] = ci[take]

    hx, hy, hz = px + tx * sm, py + ty * sm, pz + tz * sm
    u = np.where((sid == 0) | (sid == 5), hx, np.where(sid <= 2, hy, hx))
    v = np.where((sid == 0) | (sid == 5), hy, hz)
    return sid, u, v, sm, cyl


def box_hit(px, py, tx, ty, tz):
    """Backwards-compatible view of scene_hit for callers that do not care which
    cylinder was hit."""
    sid, u, v, sm, _ = scene_hit(px, py, tx, ty, tz)
    return sid, u, v, sm


def splat(acc, u, v, w, u0, u1, v0, v1):
    nv, nu = acc.shape
    fu = (u - u0) / (u1 - u0) * nu - 0.5
    fv = (v - v0) / (v1 - v0) * nv - 0.5
    iu, iv = np.floor(fu).astype(np.int64), np.floor(fv).astype(np.int64)
    du, dv = fu - iu, fv - iv
    flat = acc.ravel()
    for ou, wu in ((0, 1 - du), (1, du)):
        for ov, wv in ((0, 1 - dv), (1, dv)):
            cu, cv = iu + ou, iv + ov
            ok = (cu >= 0) & (cu < nu) & (cv >= 0) & (cv < nv)
            if ok.any():
                flat += np.bincount(cv[ok] * nu + cu[ok],
                                    weights=(w * wu * wv)[ok], minlength=nu * nv)


def sample(img, u, v, u0, u1, v0, v1):
    nv, nu = img.shape[:2]
    fu = np.clip((u - u0) / (u1 - u0) * nu - .5, 0, nu - 1.001)
    fv = np.clip((v - v0) / (v1 - v0) * nv - .5, 0, nv - 1.001)
    iu, iv = fu.astype(np.int64), fv.astype(np.int64)
    du, dv = (fu - iu)[:, None], (fv - iv)[:, None]
    return ((img[iv, iu] * (1 - du) + img[iv, iu + 1] * du) * (1 - dv) +
            (img[iv + 1, iu] * (1 - du) + img[iv + 1, iu + 1] * du) * dv)


def blur(img, sig):
    if sig < 0.35:
        return img
    r = int(np.ceil(3 * sig))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig) ** 2); k /= k.sum()
    o = img
    for ax in (0, 1):
        pad = [(0, 0), (0, 0)]; pad[ax] = (r, r)
        p = np.pad(o, pad, mode='edge')
        o = np.apply_along_axis(lambda m: np.convolve(m, k, 'valid'), ax, p)
    return o


# --------------------------------------------------------------------------- shade sail
# The sail is here as an OCCLUDER and nothing else -- the shadow gate is the
# claim under test (no caustics inside it, water still luminous), and its EDGE
# is what lands in frame.  A tensioned sail is not a flat quad, so its shadow
# edge is not a straight line: the fabric hangs in a catenary between the four
# anchors and each edge is cut in a concave scallop so it can be tensioned at
# all.  Both change the shadow's outline, so both are in the projection.  The
# sail is not otherwise drawn: it sits above the top of the frame.
SAIL_SAG = 0.24        # mid-panel droop below the bilinear surface, m
SAIL_SCAL = 0.085      # edge scallop, as a fraction of the span


def sail_surface(u, v):
    """Point on the fabric. Bilinear between the four anchors, less a catenary
    droop that vanishes at every edge (the edges are the tensioned ones)."""
    w = ((1 - u) * (1 - v))[..., None], (u * (1 - v))[..., None], \
        (u * v)[..., None], ((1 - u) * v)[..., None]
    p = w[0] * SAIL[0] + w[1] * SAIL[1] + w[2] * SAIL[2] + w[3] * SAIL[3]
    cu, cv = np.clip(u, 0, 1), np.clip(v, 0, 1)
    return p - np.stack([np.zeros_like(u), np.zeros_like(u),
                         SAIL_SAG * np.sin(np.pi * cu) * np.sin(np.pi * cv)], -1)


def sail_inside(u, v):
    c, s = SAIL_SCAL, np.sin
    return ((v > c * s(np.pi * u)) & (v < 1 - c * s(np.pi * u)) &
            (u > c * s(np.pi * v)) & (u < 1 - c * s(np.pi * v)))


# Project the fabric to z = 0 along the sun and accumulate coverage. Sampling
# (u, v) and normalising by the sample density is exact for any warped surface,
# which a polygon projection is not once the panel sags.
SX = np.linspace(X0 - 3, X1 + 3, SHADOW_N[0])
SY = np.linspace(Y0 - 3, Y1 + 3, SHADOW_N[1])
_cov = np.zeros((SHADOW_N[1], SHADOW_N[0]))
_den = np.zeros((SHADOW_N[1], SHADOW_N[0]))
_NUV = 2400
_uu = np.linspace(-0.18, 1.18, _NUV)
for _j0 in range(0, _NUV, 200):
    _U, _V = np.meshgrid(_uu, _uu[_j0:_j0 + 200])
    _P = sail_surface(_U.ravel(), _V.ravel())
    _g = _P[:, :2] - SUN_DIR[None, :2] * (_P[:, 2:3] / SUN_DIR[2])
    _m = sail_inside(_U.ravel(), _V.ravel()).astype(np.float64)
    splat(_cov, _g[:, 0], _g[:, 1], _m, SX[0], SX[-1], SY[0], SY[-1])
    splat(_den, _g[:, 0], _g[:, 1], np.ones_like(_m), SX[0], SX[-1], SY[0], SY[-1])
SHADOW = 1.0 - _cov / np.maximum(_den, 1e-9)
del _cov, _den

# soft shadow: penumbra = 0.53 deg over the sail's slant height above the water
_pen = np.deg2rad(0.53) * (SAIL[:, 2].mean() / SUN_DIR[2])
SHADOW = np.clip(blur(SHADOW, (_pen / 4.0) / ((SX[-1] - SX[0]) / SHADOW_N[0])), 0, 1)
print("sail penumbra at the water: %.0f mm" % (_pen * 1000))
print("sail shadow covers %.1f m2 of the basin" %
      ((1 - SHADOW).sum() * ((SX[-1] - SX[0]) / SHADOW_N[0]) *
       ((SY[-1] - SY[0]) / SHADOW_N[1])))


# The coping overhangs the wall, so along the WEST wall the sun never reaches the
# surface at all: it has to climb ZLIP -- now the 100 mm of the liner band, not
# the old 43 mm -- to clear the lip and it only gains
# 0.385 m per metre run, so a band of water against that wall is in shadow. The
# refracted ray from the first LIT surface then travels 1.37 m east, so what you
# see on the bed is not a dark strip against the wall but a dark strip out in the
# basin. The same test on the NORTH wall gives 7 mm: the sun is 3.75 deg north of
# due west, so it is climbing almost parallel to that wall.
#
# Written against pool_sdf, not against X0/Y1: walk from the water point toward
# the sun's azimuth until the SDF reaches the lip value SLIP. The SDF changes at
# rate (shat . grad s) along that walk, so the run to the lip is
# (SLIP - s)/(shat . grad s) -- which is why the same freeboard costs a much
# wider band on the wall the sun faces than on the wall it runs along; the two
# are printed below rather than quoted here, since ZLIP now moves. A curved
# boundary needs no new code here; only grad s changes.
_SHAT = SUN_DIR[:2] / np.linalg.norm(SUN_DIR[:2])   # horizontal, toward the sun
_LRUN = ZLIP * np.linalg.norm(SUN_DIR[:2]) / SUN_DIR[2]   # run needed to clear it
_LPEN = np.deg2rad(0.53) * (ZLIP / SUN_DIR[2])      # sun disc over that run


def _lip_run(x, y):
    """Horizontal run from (x,y) to the lip, along the sun's azimuth."""
    gx, gy, _ = pool_sdf_grad(x, y)
    adv = gx * _SHAT[0] + gy * _SHAT[1]             # d(sdf)/d(run) toward the sun
    return np.where(adv > 1e-6, (SLIP - pool_sdf(x, y)) / np.maximum(adv, 1e-6), BIG)


# The shaded band on a wall is the run projected back onto that wall's normal.
print("coping lip shades %.0f mm of water off the west wall, %.0f mm off the "
      "north wall (penumbra %.1f mm)"
      % (_LRUN * abs(_SHAT[0]) * 1000, _LRUN * abs(_SHAT[1]) * 1000, _LPEN * 1000))


def coping_vis(x, y):
    """Sun visibility at the water surface, cut by the coping lip itself. Lit
    where the run to the lip exceeds the run needed to clear ZLIP."""
    return np.clip((_lip_run(x, y) - _LRUN) / _LPEN + .5, 0, 1)


def sail_vis(x, y):
    """The sail's shadow alone. Split out from sun_vis because the freeboard
    band is a face ON the lip, not water inside it: the lip cannot shade its own
    poolward face (the bullnose rolls AWAY from the pool above it), so the band
    takes this and not the coping cut below."""
    fu = np.clip((x - SX[0]) / (SX[-1] - SX[0]) * SHADOW_N[0] - .5, 0, SHADOW_N[0] - 1.001)
    fv = np.clip((y - SY[0]) / (SY[-1] - SY[0]) * SHADOW_N[1] - .5, 0, SHADOW_N[1] - 1.001)
    iu, iv = fu.astype(np.int64), fv.astype(np.int64)
    du, dv = fu - iu, fv - iv
    return ((SHADOW[iv, iu] * (1 - du) + SHADOW[iv, iu + 1] * du) * (1 - dv) +
            (SHADOW[iv + 1, iu] * (1 - du) + SHADOW[iv + 1, iu + 1] * du) * dv)


def sun_vis(x, y):
    return sail_vis(x, y) * coping_vis(x, y)


# --------------------------------------------------------------------------- caustic pass
_norm_jets()
print("caustic pass: %.1f M rays x 4 sets" % (RAY_NX * RAY_NY / 1e6))
bed = [np.zeros((CAU_NY, CAU_NX)) for _ in range(4)]        # 0,1,2 = RGB ; 3 = mono
wall = [[np.zeros((WNV, WNU)) for _ in range(4)] for _ in range(4)]
IOR_SET = [IOR[0], IOR[1], IOR[2], IOR[1]]
# The light path gets the SAME band model as the view path -- one dispersion
# curve, used wherever a ray crosses the interface. Each ray of sets 0-2 carries
# its own wavelength drawn from its channel's band by a golden-ratio (Weyl)
# sequence on the ray index, which is maximally spread over any short run of
# neighbouring rays, so a 3 mm bed texel holding ~9 rays sees ~9 well-separated
# wavelengths rather than one. Set 3 stays strictly monochromatic at 545 nm:
# it is the controlled A/B against which all of this is read, and a mono render
# that had a band in it would prove nothing. Cost is one extra multiply per ray.
# The band the sun's own refraction spans puts 3.4 mm of extra smear on the red
# caustic at 1.40 m and 9.6 mm on the blue, against a 6.8 mm sun-disc penumbra
# -- so blue folds are physically softer than red ones, which three deltas
# could not express at all.
_PHI1 = 0.6180339887498949

rx = (np.arange(RAY_NX) + 0.5) / RAY_NX * (X1 - X0) + X0
ry = (np.arange(RAY_NY) + 0.5) / RAY_NY * (Y1 - Y0) + Y0
cell = ((X1 - X0) / RAY_NX) * ((Y1 - Y0) / RAY_NY)
CH = 256
for j0 in range(0, RAY_NY, CH):
    yy = ry[j0:j0 + CH]
    gx, gy = grad_grid(rx, yy)
    XX = np.broadcast_to(rx[None, :], gx.shape).ravel().astype(np.float32)
    YY = np.broadcast_to(yy[:, None], gx.shape).ravel().astype(np.float32)
    nx, ny, nz = normal_from_grad(gx.ravel(), gy.ravel())
    wgt = (sun_vis(XX, YY) * cell).astype(np.float64)
    live = wgt > 1e-4 * cell
    XXl, YYl = XX[live], YY[live]
    nxl, nyl, nzl, wl = nx[live], ny[live], nz[live], wgt[live]
    ql = ((np.arange(gx.size, dtype=np.float64) + j0 * RAY_NX) * _PHI1 % 1.0)[live]
    for c in range(4):
        if c == 3:
            eta_c = np.float32(1.0 / IOR_SET[c])
        else:
            lam_c = BAND[c, 0] + ((ql + c / 3.0) % 1.0) * (BAND[c, 1] - BAND[c, 0])
            eta_c = (1.0 / n_water(lam_c)).astype(np.float32)
        # AIR -> WATER, so eta < 1 and refract() has no critical angle to hit:
        # k = 1 - eta^2 sin^2(i) >= 1 - eta^2 > 0 for every normal the field can
        # produce. The assert states which side of the interface this call site
        # is on, and costs a comparison on one scalar rather than on 33 M rays.
        assert np.all(eta_c < 1.0), 'caustic launch refracts INTO the water'
        tx, ty, tz = refract(np.float32(-SUN_DIR[0]), np.float32(-SUN_DIR[1]),
                             np.float32(-SUN_DIR[2]), nxl, nyl, nzl, eta_c)
        sid, u, v, _ = box_hit(XXl, YYl, tx, ty, tz)
        # sid 0 is EVERY horizontal receiver -- floor, tread, bench top -- and
        # (u, v) is (x, y) for all of them, so one map carries the whole bed.
        # The depth each texel focuses over is bed_depth(x, y), and the rays got
        # there by being traced to it: nothing here assumes 1.40 m.
        # sid 5 is a riser. Those rays are DROPPED, which is exactly the step
        # unit's cast shadow on the floor east of it -- the light stopped there.
        m = sid == 0
        if m.any():
            splat(bed[c], u[m], v[m], wl[m], X0, X1, Y0, Y1)
        for wi, sv in enumerate((1, 2, 3, 4)):
            m = sid == sv
            if m.any():
                a, b = (Y0, Y1) if sv <= 2 else (X0, X1)
                splat(wall[wi][c], u[m], v[m], wl[m], a, b, -DEPTH, 0.0)
    if (j0 // CH) % 4 == 0:
        print("  rows %d/%d" % (j0, RAY_NY), flush=True)

bt = ((X1 - X0) / CAU_NX) * ((Y1 - Y0) / CAU_NY)
wt = [((Y1 - Y0) / WNU) * (DEPTH / WNV)] * 2 + [((X1 - X0) / WNU) * (DEPTH / WNV)] * 2
for c in range(4):
    bed[c] /= bt
    for wi in range(4):
        wall[wi][c] /= wt[wi]

cos_i = SUN_DIR[2]
sin_t = np.sqrt(1 - cos_i ** 2) / IOR[1]
cos_t = np.sqrt(1 - sin_t ** 2)
slant = DEPTH / cos_t
# The refracted sun as ONE direction under the water. Two things downstream need
# it: which faces of the step unit can be lit at all (measured near the camera
# section), and where the sail's shadow lands on the BED rather than on the
# surface -- 1.37 m east per 1.40 m of depth, which is why a shaded strip of bed
# is nowhere near under the shaded strip of water.
_thz = -SUN_DIR[:2] / np.linalg.norm(SUN_DIR[:2])
TSUN_DIR = np.array([_thz[0] * sin_t, _thz[1] * sin_t, -cos_t])


def bed_sun(x, y, z):
    """Sun visibility AT A BED POINT: sun_vis at the surface point one refracted
    slant back up the beam. Used to label the sail's shadow where it actually
    falls for the colour regression, and to check that the patches the
    diagnostics average over are not straddling its edge."""
    sl = -np.asarray(z, float) / (-TSUN_DIR[2])
    return sun_vis(x - TSUN_DIR[0] * sl, y - TSUN_DIR[1] * sl)
# The beam's transmission into the water at 69 deg incidence, from the exact
# Fresnel equations (`fresnel` above). Schlick gave 0.8729 here against the exact
# 0.8774 -- 0.5% of every photon that lights the bed, and it was the wrong 0.5%.
TSUN = float(1.0 - fresnel(cos_i)[1])                   # 12% reflects at 69 deg
print('sun elev %.1f deg -> refracted %.1f deg, offset %.2f m, slant %.2f m, T %.3f'
      % (np.degrees(np.arcsin(cos_i)), np.degrees(np.arccos(cos_t)),
         DEPTH * np.tan(np.arccos(cos_t)), slant, TSUN))
pen = np.deg2rad(0.53) * (cos_i / (IOR[1] * cos_t)) * slant
print("sun-disc penumbra on the bed at %.2f m: %.1f mm" % (DEPTH, pen * 1000))


# The caustic map is a DENSITY ESTIMATE, so its kernel has to satisfy two things
# at once: the physical sun-disc penumbra, and the bandwidth below which the
# estimator's own shot noise beats the signal. At 33.6 M rays over 32 m2 a 3 mm
# texel holds ~9 rays, so a bare texel is 33% noise. The two add in quadrature.
# This replaces a flat "1.45x physical" multiplier that used to hide the second
# term inside the first -- and hiding it there is exactly what breaks when the
# receiver is 205 mm down instead of 1.40 m, because the physical part collapses
# by 7x and the estimator's does not. SIG_EST is set to leave the 1.40 m bed
# kernel unchanged, so this is a re-derivation and not a re-tune.
SIG_EST = 0.0018        # ? density-estimator bandwidth, m: ~0.6 of a bed texel


def sig_at(d):
    """Kernel sigma for the caustic map at receiver depth d."""
    pen = np.deg2rad(0.53) * (cos_i / (IOR[1] * cos_t)) * (d / cos_t)
    return np.sqrt((pen / 4.0) ** 2 + SIG_EST ** 2)


# The penumbra is proportional to the depth it fell through, so a single blur is
# a depth bug: it would smear a 0.205 m tread with a 1.40 m disc and flatten the
# very thing the step flight exists to show. bed_depth is piecewise constant, so
# blurring per level and selecting is exact rather than approximate.
BU, BV = np.meshgrid(np.linspace(X0, X1, CAU_NX), np.linspace(Y0, Y1, CAU_NY))
BDEP = bed_depth(BU, BV)
DLEV = np.unique(np.round(BDEP, 6))
_dx = (X1 - X0) / CAU_NX
print("bed depths present: " + ", ".join(
    "%.3f m (%.0f%% of area, penumbra %.1f mm, kernel %.1f mm)"
    % (d, 100. * (BDEP == d).mean(),
       np.deg2rad(0.53) * (cos_i / (IOR[1] * cos_t)) * (d / cos_t) * 1000,
       sig_at(d) * 1000) for d in DLEV))
for c in range(4):
    raw = bed[c]
    out = blur(raw, sig_at(DEPTH) / _dx)
    if out is raw:
        out = raw.copy()
    for d in DLEV:
        if abs(d - DEPTH) < 1e-9:
            continue
        m = BDEP == d
        rr = np.flatnonzero(m.any(1)); cc = np.flatnonzero(m.any(0))
        pad = int(np.ceil(3 * sig_at(DEPTH) / _dx)) + 2
        r0, r1 = max(rr[0] - pad, 0), min(rr[-1] + pad + 1, CAU_NY)
        c0, c1 = max(cc[0] - pad, 0), min(cc[-1] + pad + 1, CAU_NX)
        sub = blur(raw[r0:r1, c0:c1], sig_at(d) / _dx)
        out[r0:r1, c0:c1] = np.where(m[r0:r1, c0:c1], sub, out[r0:r1, c0:c1])
    bed[c] = out
    # ? A wall texel at height z was lit through |z| of water, so its penumbra
    # ? runs from 0 at the waterline to the full 6.8 mm at the foot. The wall
    # ? maps are blurred at the mid-wall value instead of per row: the walls are
    # ? at most a few pixels tall in this frame and the shading below already
    # ? takes their Beer-Lambert path from |z| rather than from DEPTH.
    for wi in range(4):
        wall[wi][c] = blur(wall[wi][c], sig_at(0.5 * DEPTH) / ((Y1 - Y0) / WNU))
print("bed caustic: mean %.2f  p99 %.2f  max %.2f" %
      (bed[1].mean(), np.percentile(bed[1], 99), bed[1].max()))


# --- is the net actually depth-graded?  Measure it, do not assert it. ---------
# Cell SIZE, which is what the bar asks for, is twice the lag of the first zero
# crossing of the radially averaged autocorrelation: one bright line to the next
# dark centre and back. (Falling to 1/e instead measures the WIDTH of a bright
# line, which is a different and much smaller number -- worth saying, because
# reading the wrong one off an autocorrelogram is an easy way to declare a pass.)
def cell_size(x0, x1, y0, y1, arr=None):
    a = bed[3] if arr is None else arr
    i0, i1 = int(x0 / (X1 - X0) * CAU_NX), int(x1 / (X1 - X0) * CAU_NX)
    j0, j1 = int(y0 / (Y1 - Y0) * CAU_NY), int(y1 / (Y1 - Y0) * CAU_NY)
    p = a[j0:j1, i0:i1]
    if p.size < 4096 or p.std() < 1e-9:
        return float('nan')
    p = p - p.mean()
    F = np.fft.rfft2(p)
    ac = np.fft.irfft2(F * np.conj(F), s=p.shape)
    ac = ac / ac[0, 0]
    # Each axis is read out to ITS OWN reach and only the axes that actually
    # cross zero within it are averaged. A tread is an annulus 300 mm wide and
    # metres long, so a single lag limit taken from the short axis reports the
    # limit -- 114 mm, suspiciously close to twice a third of the patch -- and
    # calls it a cell size. Returning nan when nothing crosses is the honest
    # answer for a patch too small to hold a cell.
    est = [2.0 * np.flatnonzero(c < 0.0)[0] * _dx
           for c in (ac[:min(ac.shape[0] // 3, 200), 0],
                     ac[0, :min(ac.shape[1] // 3, 200)])
           if np.any(c < 0.0)]
    return float(np.mean(est)) if est else float('nan')

# Upwelling radiance of the lit water: liner albedo, lit through the whole light
# path and looked at through a whole depth of water. The pool is a large, bright,
# strongly coloured UPWARD source and the stone at its edge is lit by it. Without
# this term the coping's bullnose -- which faces the water and therefore faces
# away from a western sun -- comes out black, and a 3 cm black line compressed
# into two pixels at the far coping is speckle, not a shadow line. With it, it is
# the dim teal line a real pool edge has, and the coping picks up a cast from the
# water for the first half metre, which real ones visibly do.
WBOUNCE = 0.5 * LINER_TINT * 0.74 * (
    SUN_COL * cos_i * TSUN * np.exp(-ABS * (slant + DEPTH)) + SKY_AMB * 0.8)
print("water upwelling onto the coping: %s  (sky on stone: %s)"
      % (np.round(WBOUNCE, 3), np.round(SKY_DECK, 3)))


# --------------------------------------------------------------------------- materials
def liner(u, v):
    n = (0.5 + 0.5 * np.sin(u * 3.1 + .7) * np.sin(v * 4.3 - .4)
         + 0.30 * np.sin(u * 10.0 - 1.2) * np.sin(v * 8.5 + 2.1))
    a = 0.74 + 0.030 * (n - 0.6)
    a -= 0.34 * np.exp(-(((u - 4.0) / .15) ** 2 + ((v - 2.0) / .15) ** 2))
    return np.clip(a, .05, .95)[..., None] * LINER_TINT[None, None]


def tiles(u, v):
    """The wall, and specifically the last 155 mm of it. v is depth, 0 at the
    still waterline. A pool wall is not uniform down to the surface: it carries
    the two marks the surface itself leaves -- a chalky calcium bloom exactly at
    the mean level where evaporation keeps depositing the hardness, and a thin
    dirt line a couple of centimetres under it where the surface film collects
    and is never skimmed. Those two lines are the reason a real pool edge does
    not read as a cut.

    WHAT LEFT, and why. This used to put a 48 mm MOSAIC WATERLINE COURSE over
    the top 155 mm of the wall -- a different, paler, greener albedo than the
    liner under it. Bar section B2b says that is a different pool: the reference
    is a LINER pool, the sheet runs unbroken from the floor up to a bead track
    under the coping, so the colour above the water is the colour below it and
    there is no course of anything at the waterline. The band above the water is
    now built (`liner_band`), and it would have met a mosaic stripe at its own
    foot. The two marks stay: they are deposits ON the liner, not a material.

    `?` NOT FIXED HERE, and recorded rather than quietly changed: the 250 mm
    grid of 11 mm darker lines below is still a TILE grid, and a liner pool has
    no grout either. It is the rest of the wall rather than the band B2b is
    about, so it is left for whoever owns that finding."""
    lev = 0.82 + .04 * np.sin(u * 17.) * np.sin(v * 21.)
    g = ((np.abs(((u / .25) % 1.) - .5) > .456) | (np.abs(((v / .25) % 1.) - .5) > .456))
    lev = np.where(g, .70, lev)
    alb = np.broadcast_to(LINER_TINT[None, None], lev.shape + (3,)).copy()

    cal = np.exp(-((v + .0095) / .0115) ** 2)              # calcium, at mean level
    dirt = np.exp(-((v + .0330) / .0165) ** 2)             # surface film, just under
    lev = lev * (1 + .34 * cal) * (1 - .22 * dirt)
    w = (.78 * cal)[..., None]
    alb = alb * (1 - w) + np.array([.95, .91, .84])[None, None] * w
    return np.clip(lev, .04, 1.7)[..., None] * alb


def sail_glow(u, v):
    """Diffuse transmission through the fabric. What matters at a point below is
    the SOLID ANGLE the panel subtends, not whether the point is under its
    footprint -- a swimmer two metres to the side still sees most of it. Proxy:
    1/(1+(d/R)^2) about the panel centroid, R from panel size + hang height."""
    c = SAIL[:, :2].mean(0)
    R = 0.5 * np.hypot(*(SAIL[:, :2].max(0) - SAIL[:, :2].min(0))) + SAIL[:, 2].mean()
    d2 = (u - c[0]) ** 2 + (v - c[1]) ** 2
    return 1.0 / (1.0 + d2 / (R * R))


def shade(cau, alb, ao=1.0, glow=None, dep=DEPTH, extra=None):
    """Receiver radiance. `dep` is the water OVER this texel, and it is a field,
    not a constant: the light path to it is dep/cos_t and the camera-side path is
    added later from the traced distance. This is where a tonal staircase over
    the steps comes from -- exp(-a*dep) with a(red) = 0.262 is a third of a stop
    per 250 mm riser in red alone, which is what makes a tread read shallower."""
    o = np.zeros(cau[0].shape + (3,))
    sl = dep / cos_t
    for c in range(3):
        ac = alb[..., c] if alb.ndim == 3 else alb
        amb = SKY_AMB[c] * ao
        if glow is not None:
            amb = amb + SAIL_TAU * SUN_COL[c] * SUN_DIR[2] * glow
        e = (SUN_COL[c] * cos_i * TSUN * cau[c] * np.exp(-ABS[c] * sl)
             + amb * np.exp(-ABS[c] * dep * 1.55))
        if extra is not None:
            e = e + extra[..., c]
        o[..., c] = ac * e
    return o


LIN = liner(BU, BV)
GLOW = sail_glow(BU, BV)


def bed_ao(x, y, z=None):
    """Sky visibility at a bed point, cosine-weighted. Two occluders:
      * the pool walls -- 1 - 0.30 exp(-d/0.30) is a two-wall corner losing 60%.
      * every step riser standing PROUD of this point. For a straight wall of
        height h at distance a the cosine-weighted occluded fraction is exactly
        (1 - a/sqrt(a^2+h^2))/2, so the dark line that hugs the underside of each
        nosing is a closed form, not a painted gradient. The arcs are convex
        outward, so this slightly over-occludes; that is the conservative way
        round for a contact shadow."""
    ao = 1.0 - 0.30 * np.exp(pool_sdf(x, y) / 0.30)
    zz = bed_z(x, y) if z is None else z
    for (cx, cy, R, ztop) in CYL:
        a = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - R
        h = ztop - zz
        ok = (a >= 0) & (h > 0)
        a = np.maximum(a, 1e-4)
        ao = ao * np.where(ok, 1.0 - .5 * (1.0 - a / np.hypot(a, np.maximum(h, 0.))), 1.0)
    return ao


BED_AO = bed_ao(BU, BV)

# --- one bounce back off the UNDERSIDE of the surface -------------------------
# The bed is a bright Lambertian reflector and the interface above it is a
# mirror over most of its output: everything leaving beyond the critical angle
# 48.6 deg is totally internally reflected straight back down. For a cosine
# distribution the share beyond that angle is exactly 1 - 1/n^2 = 0.438 -- no
# fitting, no constant. This is the term whose absence makes a shaded bed a flat
# dark hole: the bar says the water under the sail stays clearly luminous at
# about half the lit value, and flat sky ambient through the Snell window cannot
# do that. The step unit's own cast shadow needs it for the same reason.
# It is NOT a local fill. A ray leaving 1.40 m of water at the critical angle
# lands 3.2 m away and steeper ones land further, so the return is smeared over
# metres -- which is why it is estimated on a coarse grid and why it reads as a
# lift rather than as a glow. Only ONE bounce is taken; the further ones and the
# share that lands on the walls and comes back are not modelled.
TIR_FRAC = 1.0 - 1.0 / IOR[1] ** 2
_S2C = 1.0 / IOR[1] ** 2
NRET, RNX, RNY = 2_400_000, 200, 100
_rr = np.random.default_rng(4242)
_bx = _rr.uniform(X0, X1, NRET); _by = _rr.uniform(Y0, Y1, NRET)
_bz = bed_z(_bx, _by)
_u = _S2C + (1.0 - _S2C) * _rr.random(NRET)      # sin^2(theta), cosine-weighted
_sn, _cs = np.sqrt(_u), np.sqrt(1.0 - _u)
_ph = _rr.uniform(0, 2 * np.pi, NRET)
_up = -_bz / _cs                                  # slant from bed to surface
_sx = _bx + _up * _sn * np.cos(_ph)
_sy = _by + _up * _sn * np.sin(_ph)
_ok = pool_sdf(_sx, _sy) < SLIP                   # else it met a wall on the way up
_E = np.stack([sample(shade(bed[:3], np.ones_like(BDEP), BED_AO, glow=GLOW,
                            dep=BDEP)[..., c:c + 1], _bx, _by, X0, X1, Y0, Y1)[:, 0]
               for c in range(3)], 1)             # bed irradiance at the source
_A = sample(LIN, _bx, _by, X0, X1, Y0, Y1)        # times its albedo -> flux up
_W = _A * _E * (TIR_FRAC * (X1 - X0) * (Y1 - Y0) / NRET)
_sid, _u2, _v2, _sm, _ = scene_hit(_sx[_ok], _sy[_ok],
                                   (_sn * np.cos(_ph))[_ok], (_sn * np.sin(_ph))[_ok],
                                   -_cs[_ok])
_path = (_up[_ok] + _sm)
_bch, _wch = [], [[] for _ in range(4)]
for c in range(3):
    w = _W[_ok, c] * np.exp(-ABS[c] * _path)
    acc = np.zeros((RNY, RNX))
    m = _sid == 0
    splat(acc, _u2[m], _v2[m], w[m], X0, X1, Y0, Y1)
    acc /= ((X1 - X0) / RNX) * ((Y1 - Y0) / RNY)
    # ? 1.6 coarse texels (64 mm) of smoothing on the estimate. The returned
    # ? field is genuinely smooth over metres, so this removes Monte-Carlo
    # ? variance and not signal -- but the bandwidth itself is not derived.
    _bch.append(blur(acc, 1.6))
    for wi, sv in enumerate((1, 2, 3, 4)):
        m = _sid == sv
        a, b = (Y0, Y1) if sv <= 2 else (X0, X1)
        wa = np.zeros((WNV // 4, WNU // 4))
        splat(wa, _u2[m], _v2[m], w[m], a, b, -DEPTH, 0.0)
        wa /= ((b - a) / (WNU // 4)) * (DEPTH / (WNV // 4))
        _wch[wi].append(blur(wa, 1.6))
bedret = np.stack(_bch, -1)
wallret = [np.stack(_wch[wi], -1) for wi in range(4)]
print("TIR return: %.1f%% of the bed's own output comes back down; it adds %s "
      "to the bed against %s of sky ambient"
      % (100 * TIR_FRAC, np.round(bedret.reshape(-1, 3).mean(0), 3),
         np.round(SKY_AMB * np.exp(-ABS * DEPTH * 1.55), 3)))
# ...and the reason that is so much smaller than 43.9% of a bright bed sounds:
# everything past the critical angle leaves the bed at more than 48.6 deg from
# vertical, so from 1.40 m down it needs at least 1.59 m of horizontal run to
# reach the surface at all. In a basin 4 m across, most of it meets a WALL
# first. Those rays are dropped here, which makes the wall the single largest
# unmodelled carrier of light in this scene -- see the riser gather below, which
# is the receiving half of exactly that transfer, written for a vertical face.
print("  ...but %.0f%% of it meets a wall before it reaches the surface (the "
      "unmodelled wall re-emission), and the survivors are smeared over metres"
      % (100 * (1.0 - _ok.mean())))
# HOW BIG IS THE WALL, as a light carrier?  Not by argument -- exactly. What a
# bed point can see of the SKY is the water rectangle overhead, and the
# cosine-weighted view factor from a horizontal differential element to a
# parallel rectangle is closed form; split the rectangle at the point's own
# (x, y) and sum the four quadrants:
#   F(a, b, h) = (1/2pi)[ (a/r_a) atan(b/r_a) + (b/r_b) atan(a/r_b) ],
#   r_a = sqrt(a^2 + h^2),  r_b = sqrt(b^2 + h^2)
# Everything left over is WALL, and every bit of that is currently being
# credited to SKY_AMB. This is the size of the missing term, and the number to
# weigh a wall-re-emission pass against -- see the README backlog.
def _sky_vf(x, y, h):
    tot = 0.
    for a in (x - X0, X1 - x):
        for b in (y - Y0, Y1 - y):
            ra, rb = np.hypot(a, h), np.hypot(b, h)
            tot = tot + (a / ra * np.arctan(b / ra)
                         + b / rb * np.arctan(a / rb)) / (2 * np.pi)
    return tot


_WSH = 1.0 - _sky_vf(BU, BV, np.maximum(BDEP, 1e-3))
print("  the walls take %.1f%% of the bed's cosine-weighted hemisphere on "
      "average (%.0f%% at the worst texel, exact rectangle view factor) -- and "
      "SKY_AMB is applied over the WHOLE of it, so the flat ambient is "
      "over-counted by that share and the directional wall term that should "
      "replace it is missing" % (100 * _WSH.mean(), 100 * _WSH.max()))
BEDRET = np.stack([sample(bedret[..., c:c + 1], BU.ravel(), BV.ravel(),
                          X0, X1, Y0, Y1)[:, 0].reshape(BU.shape)
                   for c in range(3)], -1)

bed_img = {'disp': shade(bed[:3], LIN, BED_AO, glow=GLOW, dep=BDEP, extra=BEDRET),
           'mono': shade([bed[3]] * 3, LIN, BED_AO, glow=GLOW, dep=BDEP, extra=BEDRET)}
# ...and THE SAME BED WITH THE WATER TAKEN OUT of the light leg, which is the
# reference half of the absorption regression the freeboard band makes possible:
# the dry band and the bed are one pigment differing by one path, so bed_img /
# BED_DRY is that path, measured on the maps the picture is actually made from
# rather than argued from constants. Costs one more `shade`; nothing samples it.
BED_DRY = shade(bed[:3], LIN, BED_AO, glow=GLOW, dep=np.zeros_like(BDEP),
                extra=BEDRET)
wall_img = {'disp': [], 'mono': []}
for wi in range(4):
    uu = np.linspace(Y0, Y1, WNU) if wi < 2 else np.linspace(X0, X1, WNU)
    UU, VV = np.meshgrid(uu, np.linspace(-DEPTH, 0.0, WNV))
    T = tiles(UU, VV)
    WR = np.stack([sample(wallret[wi][..., c:c + 1], UU.ravel(), VV.ravel(),
                          uu[0], uu[-1], -DEPTH, 0.)[:, 0].reshape(UU.shape)
                   for c in range(3)], -1)
    # the coping overhangs the wall by 20 mm, so the last few centimetres of wall
    # sit in its shade: the darkest thing in the pool is the line under the lip.
    WAO = .78 * (1.0 - .32 * np.exp(VV / .055))
    wall_img['disp'].append(shade(wall[wi][:3], T, WAO, dep=-VV, extra=WR))
    wall_img['mono'].append(shade([wall[wi][3]] * 3, T, WAO, dep=-VV, extra=WR))

# WHAT THE MISSING WALL TERM IS WORTH, now that both halves of it exist as
# numbers in one place. `_WSH` above is exactly the cosine-weighted FRACTION of a
# bed point's hemisphere that is wall, in the same normalisation the riser gather
# closes on -- (1/pi) INT cos dw over the hemisphere is 1 -- so a wall of mean
# outgoing radiance L contributes L * _WSH in the units `shade` calls `amb`, and
# what is being applied over that same share today is SKY_AMB. The difference,
# per channel, IS the error, and it is signed:
_LW = np.mean([w.reshape(-1, 3).mean(0) for w in wall_img['disp']], 0)
_ERR = _WSH.mean() * (_LW - SKY_AMB * np.exp(-ABS * DEPTH * 1.55))
print("the wall as a light carrier, priced: mean wall radiance %s against %s of "
      "sky ambient reaching the bed. Over the %.1f%% of the hemisphere the walls "
      "take, swapping one for the other would move the bed's ambient by %s per "
      "channel -- signed, so the sign of each channel is the direction the flat "
      "constant is wrong in."
      % (np.round(_LW, 3), np.round(SKY_AMB * np.exp(-ABS * DEPTH * 1.55), 3),
         100 * _WSH.mean(), np.round(_ERR, 3)))
_wtop = np.mean([w[int(WNV * .95):].reshape(-1, 3).mean(0) for w in wall_img['disp']], 0)
_wbot = np.mean([w[:int(WNV * .05)].reshape(-1, 3).mean(0) for w in wall_img['disp']], 0)
print("  ...and it is not a constant to be corrected: the wall runs %s at the "
      "waterline to %s at its foot, a factor %.1f in green over 1.40 m, so what "
      "replaces SKY_AMB there has to be DIRECTIONAL. That is the return leg, and "
      "it needs an UP-GOING intersector that scene_hit is not."
      % (np.round(_wtop, 3), np.round(_wbot, 3),
         _wtop[1] / max(_wbot[1], 1e-9)))

# --- ONE BOUNCE OFF THE BED, ONTO THE RISERS ---------------------------------
# The step region rendered NEUTRAL GREY: median sRGB (119, 128, 141) at
# saturation 0.16, against 0.42 for open water in the SAME image row and 0.69
# for the floor nearer the camera. Same row is the same grazing angle and the
# same Fresnel, so the surface reflection was not the cause; the receiver was.
# The bar says the saturation comes from the liner and that the water column can
# only subtract, so a near-neutral region is a statement that light reached the
# camera without going through water or off the liner. What was happening is
# arithmetic: the riser's own radiance was so low that the (horizon-coloured,
# nearly neutral) sky reflection won by default at 36% Fresnel.
#
# WHY THE RISER HAS ALMOST NOTHING. The refracted sun runs east at 44.4 deg from
# vertical, so a face is lit only if it faces west of the underwater terminator;
# an anti-solar camera looks at east-facing surfaces by construction. The two
# sets barely intersect, and the print further down MEASURES the overlap rather
# than asserting it away: about 6% of the riser arc is both lit and visible, and
# nowhere on it does min(N.L, N.V) exceed 0.10 -- the sun 84 deg off the normal
# on a face the camera sees 84 deg off the normal. So direct sun on a visible
# riser is not identically zero, it is a grazing tenth of one term on a sliver
# a few pixels wide. The appearance of the step region is indirect light, and
# the model had exactly one indirect term: SKY_AMB * ao, a flat blue DC through
# the Snell window.
#
# THE MISSING TERM is one bounce off the sunlit tread and floor a few
# centimetres in front of the riser. Measured below it is (0.13, 0.57, 0.72)
# against (0.28, 0.45, 0.71) of sky on the same face -- comparable in blue,
# larger in green, smaller in red -- so it does not merely brighten the riser,
# it MOVES ITS COLOUR, which is the whole of the defect. It is also the only one
# of the two that carries structure: the liner is a diffuse reflector of albedo
# (0.24, 0.54, 0.70) carrying the caustic net, and a real riser visibly shows
# the net moving on it.
#
# IT IS A GATHER, NOT A FORM FACTOR, for two reasons. The pattern is the point --
# a form factor would deliver the right energy with no net on it. And the bed a
# riser sees is a staircase, not a plane: the tread in front carries the riser's
# OWN shadow, from 235 mm of its 300 mm at the east end of the sweep down to
# 16 mm at the south point, so the nearest and most heavily weighted part of the
# source is the dark part; the floor beyond is in full sun 0.7 m lower; and the
# outer nosing hides some of that floor. No closed form spans those.
#
# THE ESTIMATOR integrates over the downgoing half of the hemisphere in front of
# the face -- a quarter sphere, pi sr -- which is exactly the half a vertical
# face can see the bed through; the upgoing half is the sky term already there,
# so the two partition the hemisphere and nothing is counted twice. It returns
#   E = (1/pi) * INT L cos(t) dw          -> 0.500 for a uniformly bright bed,
# L being the same albedo*irradiance product that shade() returns, and 0.500 is
# printed below as a regression test on the quadrature.
#
# HOW THE DIRECTIONS ARE CHOSEN, and why the previous choice destroyed the very
# thing this term exists to deliver. Cosine-weighted directions are the right
# estimator for IRRADIANCE and they fixed the colour -- but they are drawn
# without reference to the bed, so the 128 hit points landed anywhere from 5 cm
# to 8 m away and only ~10 of them fell inside any one 20 cm caustic cell. The
# set was shared by every texel, so that under-resolution is not pixel noise: it
# is a fixed comb convolved with the caustic field, and it produced a smooth
# blotch of the same amplitude as the pattern it was hiding. Measured: the map
# carried rms/mean 0.30-0.37, all of it at scales far coarser than a cell.
#
# The fix is to importance-sample by DISTANCE ALONG THE BED, which is where the
# structure lives. Sample (d, phi): d log-uniform on [D0, D1] and phi uniform on
# (-pi/2, pi/2) about the outward normal, then aim at the point that far away on
# the plane through this riser's own foot, at height h under the sample point:
#     beta = atan(h/d),  w_hat = cos(beta)(cos(phi) n_hat + sin(phi) t_hat) - sin(beta) z
# The solid-angle Jacobian is dw = d h/(h^2+d^2)^{3/2} dd dphi, so with those
# pdfs the estimator weight is closed form:
#     w = ln(D1/D0) * cos(phi) * d^3 h / (h^2 + d^2)^2
# and its expectation over the full range is exactly 1/2 -- the same closure as
# before, now with the truncation to [D0, D1] priced explicitly (printed below).
# Nothing about the physics changed: same hemisphere, same cosine, same traced
# occlusion. What changed is that the sample points now form a fixed POLAR
# LATTICE ABOUT EACH TEXEL, log-spaced so every octave of distance gets the same
# number of samples. A lattice that moves rigidly with the receiver turns the
# gather into a convolution with a smooth kernel, which is exactly what a
# near-field-dominated irradiance is; the previous comb could not be.
# Half the weight comes from inside 30 cm for a texel 12 cm up (closed form:
# (2/pi) INT_0^a d^2 h/(h^2+d^2)^2 dd = 0.539 at a = 0.30, h = 0.12), so this is
# where the estimator has to be sharp and where the log spacing puts it.
RIS_NT, RIS_NZ = 512, 24        # arc samples per cylinder (18 mm), height samples
RIS_ND, RIS_NP = 20, 12         # distance strata x azimuth strata = 240 directions
RIS_D0, RIS_D1 = 0.006, 120.0   # sampled range of bed distance, m. The upper
                                # end is far past the 8.9 m basin diagonal on
                                # purpose: those are the near-horizon directions
                                # that see the far WALL, and cutting them off
                                # would show up as a closure deficit rather than
                                # as a wrong picture. Priced exactly, below.
RIS_HMIN = 0.020                # ? importance-sampling floor on the reference
                                # ? height. It changes only the pdf, never the
                                # ? estimate: a texel sitting on its own foot has
                                # ? h -> 0 and the whole lattice would collapse
                                # ? onto the horizon. 20 mm is chosen.
_rr2 = np.random.default_rng(90210)
_lnR = np.log(RIS_D1 / RIS_D0)
_DD = RIS_D0 * np.exp(_lnR * ((np.arange(RIS_ND)[:, None]
                               + _rr2.random((RIS_ND, RIS_NP))) / RIS_ND)).ravel()
_PH = (np.pi * ((np.arange(RIS_NP)[None, :] + _rr2.random((RIS_ND, RIS_NP)))
                / RIS_NP) - np.pi / 2).ravel()


def _ris_closure(h, d0, d1):
    """Exact (2/pi) INT_d0^d1 d^2 h/(h^2+d^2)^2 dd -- what fraction of the 0.500
    the truncated distance range can reach. The part outside it is light from
    directions the lattice never sends a ray in, so it is a real, priced loss."""
    f = lambda d: h * (-d / (2 * (h * h + d * d)) + np.arctan(d / h) / (2 * h))
    return (2 / np.pi) * (f(d1) - f(d0))


RIS_MAP, RIS_FOOT, _mbs = [], [], []
_rstat = np.zeros(3)                        # [bed+wall hits, riser hits, samples]
_rtrunc = []
for _i, (_cx, _cy, _R, _zt) in enumerate(CYL):
    _th = (np.arange(RIS_NT) + .5) / RIS_NT * 2 * np.pi
    _ct, _st = np.cos(_th), np.sin(_th)
    # the riser's FOOT is whatever the bed does just outside this cylinder --
    # the next tread down, or the floor. Read, not tabulated, so the map needs
    # no edit when a level moves.
    _zf = np.minimum(bed_z(_cx + (_R + 2e-3) * _ct, _cy + (_R + 2e-3) * _st),
                     _zt - 1e-3)
    RIS_FOOT.append(_zf)
    _tt = (np.arange(RIS_NZ) + .5) / RIS_NZ
    _Z = (_zf[None, :] + _tt[:, None] * (_zt - _zf)[None, :])
    _PX = np.broadcast_to(_cx + _R * _ct, _Z.shape).ravel()
    _PY = np.broadcast_to(_cy + _R * _st, _Z.shape).ravel()
    _NX = np.broadcast_to(_ct, _Z.shape).ravel().copy()
    _NY = np.broadcast_to(_st, _Z.shape).ravel().copy()
    _PZ = _Z.ravel()
    # Only the arc INSIDE the basin is traced. The other half of a wall-set unit
    # is behind the wall, where a ray leaves the box immediately and every
    # distance is negative: garbage, and it would poison the map's neighbours
    # through the bilinear read at the wall.
    _ix = np.flatnonzero(pool_sdf(_PX, _PY) < 0.0)
    _PX, _PY, _PZ2 = _PX[_ix], _PY[_ix], _PZ[_ix]
    _NX, _NY = _NX[_ix], _NY[_ix]
    # the reference height of each texel over its own foot: the height that
    # decides where a given down-angle lands on the bed. Only the pdf uses it.
    _HH = np.maximum(_PZ2 - np.broadcast_to(_zf, _Z.shape).ravel()[_ix], RIS_HMIN)
    _rtrunc.append(_ris_closure(_HH, RIS_D0, RIS_D1))
    _acc = np.zeros((_PZ.size, 3))
    for _d, _ph in zip(_DD, _PH):
        _r2 = _HH * _HH + _d * _d
        _cb, _sb = _d / np.sqrt(_r2), _HH / np.sqrt(_r2)   # cos, sin of the dip
        _cp, _sp = np.cos(_ph), np.sin(_ph)
        _tx = _cb * (_NX * _cp - _NY * _sp)
        _ty = _cb * (_NY * _cp + _NX * _sp)
        _tz = -_sb
        _sd, _u, _v, _sm, _ = scene_hit(_PX + _NX * 1e-4, _PY + _NY * 1e-4,
                                        _tx, _ty, _tz, _PZ2)
        _col = np.zeros((_PZ2.size, 3))
        _m = _sd == 0
        if _m.any():
            _col[_m] = sample(bed_img['mono'], _u[_m], _v[_m], X0, X1, Y0, Y1)
        for _wi, _sv in enumerate((1, 2, 3, 4)):
            _m = _sd == _sv
            if _m.any():
                _a, _b = (Y0, Y1) if _sv <= 2 else (X0, X1)
                _col[_m] = sample(wall_img['mono'][_wi], _u[_m], _v[_m],
                                  _a, _b, -DEPTH, 0.)
        # ? a gather ray that lands on ANOTHER riser contributes nothing. Those
        # ? faces are the dark side of the same terminator, so the error is one
        # ? bounce of a dim source; the share is printed and it is under 2%.
        _w = _lnR * _cp * _d ** 3 * _HH / (_r2 * _r2)
        _acc[_ix] += _col * _w[:, None] * np.exp(-ABS[None] * _sm[:, None])
        _rstat += [_w[_sd != 5].sum(), _w[_sd == 5].sum(), _sd.size]
    _acc /= (RIS_ND * RIS_NP)
    _mbs.append(_acc[_ix].mean(0))
    RIS_MAP.append(_acc.reshape(RIS_NZ, RIS_NT, 3))
print("riser bounce: %d faces x %d directions; view-factor closure %.3f of the "
      "0.500 a vertical face has by geometry (%.3f of it is the truncation to "
      "%.0f mm - %.0f m, %.1f%% is rays dropped on another riser)"
      % (4 * RIS_NT * RIS_NZ, RIS_ND * RIS_NP, _rstat[0] / max(_rstat[2], 1),
         np.mean(np.concatenate(_rtrunc)), 1000 * RIS_D0, RIS_D1,
         100 * _rstat[1] / max(_rstat[2], 1)))
print("  it adds %s of irradiance against %s of sky ambient on the same face "
      "-- and unlike the sky term it carries the caustic net"
      % (np.round(np.mean(_mbs, 0), 3), np.round(SKY_AMB * 0.5, 3)))


# --- does it actually CARRY the net?  Measure, do not assert. ----------------
# The number that matters is not the map's total variance -- a self-shadow
# gradient running round the arc gives that for free -- but the variance at
# CAUSTIC SCALE. So the map is high-passed along the arc at 0.60 m (three cells
# of the 20 cm net) and the residual is compared with the same high-pass applied
# to the bed radiance the gather is reading, sampled along the line 60 mm
# outside the same arc. The ratio is the fraction of the bed's own cell-scale
# contrast that survives the hemisphere integral, and it has a ceiling well
# under 1: a receiver 100-300 mm from the bed integrates over about one and a
# half cells, so losing most of it is correct and losing all of it is not.
def _hipass(a, w):
    k = max(int(round(w)), 3)
    p = np.concatenate([a[-k:], a, a[:k]])
    c = np.cumsum(np.insert(p, 0, 0.))
    sm = (c[2 * k + 1:] - c[:-2 * k - 1]) / (2 * k + 1)
    return a - sm[:a.size]


print("  cell-scale contrast carried (rms of a 0.60 m high-pass along the arc, "
      "over the mean):")
for _i, (_cx, _cy, _R, _zt) in enumerate(CYL):
    _th = (np.arange(RIS_NT) + .5) / RIS_NT * 2 * np.pi
    _px, _py = _cx + _R * np.cos(_th), _cy + _R * np.sin(_th)
    _ok = pool_sdf(_px, _py) < 0
    if _ok.sum() < 32:
        continue
    _kk = 0.30 / (2 * np.pi * _R / RIS_NT)          # half-window in samples
    _rr3 = RIS_MAP[_i][RIS_NZ // 2, :, 1]
    _bb = sample(bed_img['mono'][..., 1:2], _cx + (_R + .06) * np.cos(_th),
                 _cy + (_R + .06) * np.sin(_th), X0, X1, Y0, Y1)[:, 0]
    _hr, _hb = _hipass(_rr3, _kk)[_ok], _hipass(_bb, _kk)[_ok]
    print("    cyl %d R=%.2f m:  riser %.3f   bed beside it %.3f   -> %.0f%% "
          "of the bed's own" % (_i, _R, _hr.std() / max(_rr3[_ok].mean(), 1e-9),
                                _hb.std() / max(_bb[_ok].mean(), 1e-9),
                                100 * (_hr.std() / max(_hb.std(), 1e-12))
                                * (_bb[_ok].mean() / max(_rr3[_ok].mean(), 1e-9))))

# The TIR return arrives at SHALLOW angles -- everything the bed emits beyond the
# critical angle 48.6 deg comes back down between 48.6 and 90 deg from vertical --
# so a vertical face intercepts it BETTER than the horizontal bed the bedret map
# is normalised for.
#
# START FROM RADIANCE, NOT FROM FLUX. Under the mirror the field arriving at a
# point is a UNIFORM radiance L over the cone t > tc: a Lambertian bed's radiance
# is angle-independent by definition, radiance is conserved along a ray, and a
# perfect mirror preserves it. So each receiver's irradiance is its own cosine
# integrated against that uniform radiance and NOTHING ELSE:
#
#   E_horiz = INT_{t>tc} L cos t dw            = 2 pi L INT cos t sin t dt
#                                              = pi L cos^2(tc)
#   E_vert  = INT_{t>tc} L (sin t cos ph)^+ dw = 2   L INT sin^2 t dt
#                                              = L (pi/2 - tc + sin tc cos tc)
#   TIR_VERT = (pi/2 - tc + sin tc cos tc) / (pi cos^2 tc)  =  0.885  at n = 1.3348
#
# (the vertical face's azimuth integral is INT max(cos ph, 0) dph = 2, not 2 pi).
#
# WHAT WAS WRONG, AND IT IS WORTH KEEPING. This shipped 0.563, from writing the
# arriving field as the EMITTED FLUX density `cos t sin t dt` and then
# multiplying by the receiver's cosine. That density is the right weight for a
# flux FRACTION -- it is exactly how TIR_FRAC = 1 - 1/n^2 is derived one screen
# up -- and it is the wrong weight for a receiver's irradiance from a distributed
# source, because `cos t sin t` ALREADY carries the horizontal receiver's own
# cosine. Carrying it into the vertical case leaves a spurious cos t in the
# integrand; the shipped expression then had one further stray sin t on top of
# that. Three numbers came out of one sentence: 0.563 shipped, 0.635 from the
# comment's own words, 0.885 from the physics. Both of validate.py's rows
# asserted 0.635, because its quadrature AND its Monte-Carlo were written from
# that comment rather than from the interface -- two "independent" methods
# sharing one wrong premise and agreeing with each other. Satisfying the suite
# would have moved the code onto the middle number.
#
# THE CHECK THAT CANNOT SHARE THE PREMISE: as tc -> 0 the cone opens to the whole
# hemisphere and the ratio must go to EXACTLY 1/2 -- a vertical face collects half
# of what a horizontal one does under a uniform hemisphere. That is the same 1/2
# the riser gather's estimator closes on, by a completely different integral over
# the same geometry, and validate.py now asserts both against each other.
def tir_vert(tc):
    """Vertical-face / horizontal-bed irradiance from a uniform radiance filling
    the cone t > tc. Exact; tir_vert(0) == 1/2 identically."""
    return ((np.pi / 2 - tc + np.sin(tc) * np.cos(tc))
            / (np.pi * np.cos(tc) ** 2))


TIR_VERT = float(tir_vert(np.arcsin(1.0 / IOR[1])))
print("  TIR return on a vertical face: %.3f of its value on the bed "
      "(hemisphere limit %.3f)" % (TIR_VERT, tir_vert(0.0)))


def riser_bounce(x, y, z, ci):
    """Bilinear read of the bounce map. Theta wraps; height is normalised to the
    riser's own foot, so a 240 mm riser and the 700 mm drop to the floor carry
    the same map without either being resampled."""
    out = np.zeros((x.size, 3))
    for i, (cx, cy, R, ztop) in enumerate(CYL):
        m = ci == i
        if not m.any():
            continue
        fa = (np.arctan2(y[m] - cy, x[m] - cx) % (2 * np.pi)) / (2 * np.pi) * RIS_NT - .5
        ja = np.floor(fa).astype(np.int64)
        fj = (fa - ja)[:, None]
        j0, j1 = ja % RIS_NT, (ja + 1) % RIS_NT
        zf = RIS_FOOT[i][j0] * (1 - fj[:, 0]) + RIS_FOOT[i][j1] * fj[:, 0]
        fb = np.clip((z[m] - zf) / np.maximum(ztop - zf, 1e-6), 0, 1) * RIS_NZ - .5
        kb = np.clip(fb, 0, RIS_NZ - 1.001).astype(np.int64)
        fk = np.clip(fb - kb, 0, 1)[:, None]
        A = RIS_MAP[i]
        out[m] = ((A[kb, j0] * (1 - fj) + A[kb, j1] * fj) * (1 - fk) +
                  (A[kb + 1, j0] * (1 - fj) + A[kb + 1, j1] * fj) * fk)
    return out

# --- the depth ladder, measured ----------------------------------------------
# F = 0.25 d s k with s and k taken from the field itself over the water that
# actually lights each receiver, so the number moves with the depth and nothing
# else. Cell size is the autocorrelation reading, in the same units the bar uses.
from field import grad_grid as _gg
import field as _fld


def _sk(x0, x1, y0, y1):
    xs = np.linspace(x0, x1, 192).astype(np.float32)
    ys = np.linspace(y0, y1, 192).astype(np.float32)
    gx, gy = _gg(xs, ys)
    # ONE slope convention, and it is field.py's: s = sqrt(<|grad h|^2>), the
    # total mean-square slope. This line used to divide by 2 -- the per-axis rms,
    # smaller by sqrt(2) -- while the F(net) column beside it was fed
    # field.REVERB_RMS, which is total. Two units in one printed table, which is
    # exactly the defect the surface lane had just removed from field.py. Calling
    # rms_slope rather than writing the expression out again is the fix that
    # sticks: there is now no second place where the convention can drift.
    s = _fld.rms_slope(gx, gy)
    dx, dy = (x1 - x0) / 191., (y1 - y0) / 191.
    P = np.abs(np.fft.rfft2(gx)) ** 2 + np.abs(np.fft.rfft2(gy)) ** 2
    kx = 2 * np.pi * np.fft.rfftfreq(192, dx)[None, :]
    ky = 2 * np.pi * np.fft.fftfreq(192, dy)[:, None]
    P[0, 0] = 0.0
    return s, np.sqrt((P * (kx * kx + ky * ky)).sum() / P.sum())


# Each patch is the largest rectangle that fits inside its own level -- a 1.0 m
# chord of a 300 mm annulus, not a 170 mm square -- because the autocorrelation
# below can only see a 20 cm cell if the patch is several cells long, and the
# floor patch is east of where the sail's shadow lands ON THE BED (x 2.6-5.7,
# one refracted offset east of where it lands on the water). A patch straddling
# that edge reports the shadow's own width as the cell size: it read 438 mm.
_PATCH = [("top tread   ", STEP_Z[0], 5.42, 6.58, 3.35, 3.97),
          ("2nd tread   ", STEP_Z[1], 5.50, 6.50, 2.92, 3.23),
          ("bench       ", BENCH_Z, 2.65, 3.35, 3.65, 3.98),
          ("3rd tread   ", STEP_Z[2], 5.50, 6.50, 2.60, 2.90),
          ("floor       ", -DEPTH, 5.90, 7.40, 0.70, 2.10)]
# F is a PER-BAND number -- that is the whole point of field.py's slope budget --
# so the net-writing band is what decides whether a receiver has a legible net.
# REVERB at 19.7 cm writes it; the all-band column is the same formula fed the
# slope-energy-weighted k, which the capillary floor drags down to ~8 cm and
# which therefore says "past focus" about water that plainly is not. Both are
# printed because reporting only the second is exactly the mistake the slope
# budget exists to catch. Corrected to the total-mss convention the F(all) column
# now crosses 1.0 on the floor -- so the all-band reading says "past focus" about
# the one receiver whose net is plainly legible in the frame. That does not
# weaken the argument above, it is the argument: a slope-energy-weighted k that
# the 2.8 cm capillary band drags to ~9.6 cm is the wrong k to put in F.
_KNET = _fld._plane_k(_fld.REVERB)
print("  receiver      depth  F(net,%.0fcm)  s_all  k_all  F(all)  cell   sun"
      % (200 * np.pi / _KNET))
for nm, zz, x0, x1, y0, y1 in _PATCH:
    d = -zz
    # The water that lights this patch sits one refracted offset to the WEST.
    # The window over it is a fixed 1.2 m square rather than the patch's own
    # footprint: a tread patch is 170 mm across the annulus, and a window
    # narrower than a couple of wavelengths cannot see the 20 cm band at all --
    # it measures the capillary floor and reports it as k, which is how the
    # 2nd tread came out at k = 166 (3.8 cm) with the same water beside it at 66.
    off = d * np.tan(np.arccos(cos_t))
    xa = min(max(.5 * (x0 + x1) - off, X0 + .65), X1 - .65)
    ya = min(max(.5 * (y0 + y1), Y0 + .65), Y1 - .65)
    s, k = _sk(xa - .6, xa + .6, ya - .6, ya + .6)
    _pu, _pv = np.meshgrid(np.linspace(x0, x1, 40), np.linspace(y0, y1, 40))
    print("  %s %5.3f m     %5.2f      %.3f %6.1f  %5.2f  %4.0f mm  %3.0f%%"
          % (nm, d, 0.25 * d * _fld.REVERB_RMS * _KNET, s, k,
             0.25 * d * s * k, 1000 * cell_size(x0, x1, y0, y1),
             100 * bed_sun(_pu, _pv, zz).mean()))


# --------------------------------------------------------------------------- sky
# The sun and its aureole live in the environment as three cos^n lobes. They are
# named here rather than written inline because they are the ONLY angular
# structure in this sky narrower than the reflection ellipse the footprint
# filter creates below -- the sky gradient itself turns over 90 degrees and a
# few degrees of blur does nothing to it, which is what makes convolving the
# lobes alone the whole of the job and not an approximation of convenience.
# A cos^n lobe is exp(-n th^2 / 2) near its peak, so its per-axis angular
# variance is 1/n, and its flux over the hemisphere is 2 pi / (n + 1).
#
# ALL SIX NUMBERS BELOW WERE GUESSES AND ARE NOW DERIVED. The audit that used to
# sit under this block priced the guess: the disc lobe's peak was 1563x under the
# sun's own radiance and 7.8x too wide, and the three lobes together carried a
# 35th of the direct beam. That is the whole of bar section C's complaint -- a
# broad dim smear where the physics has a small blinding point -- so this round
# replaces the amplitudes and the widths with the atmosphere.
#
# --- THE ATMOSPHERE, READ BACK OUT OF A CONSTANT THIS FILE ALREADY HAD --------
# SUN_COL's COLOUR is not a choice. exp(-m tau_Rayleigh) at the bar's own air
# mass 2.77, evaluated at this file's own three band centres and normalised to
# red, is (1.0000, 0.8921, 0.6740); SUN_COL's triple is (1.000, 0.892, 0.674).
# One part in 10^4 on two channels. So the beam that lights this scene has been
# through a RAYLEIGH atmosphere at the stated air mass and nothing else, which
# fixes three things at once: the air mass is not free, the reddening is not a
# grade, and the aerosol optical depth SUN_COL was written with is ZERO. Every
# lobe below is built on that atmosphere, and the one place a number is added to
# it rather than read out of it is marked.
def _tau_rayleigh(lam_um):
    """Whole-atmosphere Rayleigh optical depth at sea level: the standard
    0.008569 lam^-4 form with its two dispersion corrections (Hansen & Travis
    1974). Not fitted here -- it is what makes the check above a check."""
    return 0.008569 * lam_um ** -4 * (1. + 0.0113 * lam_um ** -2
                                      + 0.00013 * lam_um ** -4)


AIRMASS = 2.77                                     # the bar's, for elevation 21
TAU_R = _tau_rayleigh(np.array([620., 545., 460.]) / 1000.)
_TRAY = np.exp(-AIRMASS * TAU_R)
print("atmosphere, read back out of SUN_COL rather than assumed:")
print("  Rayleigh tau %s at 620/545/460 nm -> exp(-m tau)/red = %s at m = %.2f, "
      "against SUN_COL's own %s. The sun's COLOUR in this file IS Rayleigh "
      "extinction at the bar's air mass, to 1e-4, so the atmosphere it was "
      "written with carries tau_aerosol = 0."
      % (np.round(TAU_R, 4), np.round(_TRAY / _TRAY[0], 4), AIRMASS,
         np.round(SUN_COL / SUN_COL[0], 4)))

# --- LOBE 1, THE DISC: nothing free at all -----------------------------------
# `shade` uses SUN_COL as E_n/pi, so E_n = pi*SUN_COL is the normal irradiance
# and the disc's radiance is E_n / Omega_sun with Omega_sun the disc's own solid
# angle. A cos^n lobe carries 2 pi / (n + 1); setting that equal to Omega_sun
# gives n = 2/theta_s^2 - 1 and then a peak of L_sun makes the lobe's FLUX equal
# the direct beam exactly. Peak, width and flux all land on the sun at once --
# there is no amplitude left to choose, which is the point.
THETA_SUN = np.deg2rad(0.53) / 2.0                 # solar angular radius
OMEGA_SUN = np.pi * THETA_SUN ** 2                 # 6.72e-5 sr
E_SUN = np.pi * SUN_COL                            # normal irradiance, 24.1 green
L_SUN = E_SUN / OMEGA_SUN                          # 3.59e5 green
N_DISC = 2.0 / THETA_SUN ** 2 - 1.0                # 93493

# --- LOBE 2, THE AUREOLE THIS ATMOSPHERE ACTUALLY HAS ------------------------
# The aureole is single-scattered sunlight and its radiance follows from the
# same plane-parallel integral the beam does. Scattering at optical depth tau'
# feeds the view direction at F_0 exp(-tau'/mu_0) omega P(Theta) / (4 pi) and the
# result is attenuated out again; in the sun's OWN direction mu = mu_0, the
# integral collapses to F_0 m tau exp(-m tau) P / (4 pi), and F_0 exp(-m tau) is
# the beam that arrives, which is E_n. So
#     L(Theta) = (E_n / 4 pi) P(Theta) m tau_sca
# with no free scale: the aureole is the beam times a phase function times the
# slant scattering optical depth, and the atmosphere above has already fixed
# tau_sca -- it is tau_Rayleigh, whose single-scattering albedo is exactly 1.
#
# Rayleigh's phase function is 3/4 (1 + cos^2 Theta), which splits into an
# ISOTROPIC 3/4 -- a uniform sky, which is what SKY_HOR/SKY_TOP and their
# elevation gradient already carry -- plus 3/4 cos^2 Theta, which is the whole
# of the forward structure a Rayleigh atmosphere has. cos^2 IS a cos^n lobe,
# with n = 2, so the aureole needs no fitting at all:
#     amp = (E_n / 4 pi) m tau_R * 3/4,   n = 2.
# It is broad and it is faint -- 0.4 against a sky of about 1.0 -- and that is
# the point: a clean atmosphere has no compact aureole, because a compact
# aureole is a DIFFRACTION peak and diffraction needs particles.
N_AURE = 2.0
L_AURE = (E_SUN / (4. * np.pi)) * AIRMASS * TAU_R * 0.75

# --- LOBE 3, THE AEROSOL AUREOLE: DERIVED TO ZERO, AND MEASURED THERE --------
# What is NOT here, and why, because its absence is a result rather than an
# omission. A real coastal afternoon carries tau_a ~ 0.1 of aerosol, and an
# aerosol aureole is a genuine feature: for particles large against the
# wavelength the extinction efficiency tends to 2 and exactly HALF of it is
# diffraction -- the Airy pattern of the particle's own shadow -- which is a
# forward peak a few degrees wide, the aureole a photographer sees. The other
# half is refraction and reflection, broad, Henyey-Greenstein at the asymmetry
# quoted for tropospheric aerosol. Two mechanisms, two widths, one optical
# depth: the previous cos^260 and cos^14 were sitting almost exactly on those
# two widths, which is why only their amplitudes were wrong.
#
# THE REASON IT IS ZERO IS ENERGY, NOT TASTE. SUN_COL's colour is Rayleigh
# extinction alone, so the beam that lights this frame was never dimmed by
# aerosol. Adding aerosol scattering to the environment without removing it from
# the beam creates the light twice, and it creates it exactly where a reflection
# is most sensitive to it. Dimming the beam instead means changing SUN_COL,
# which relights every diffuse surface in the frame and is a round of its own.
# So the environment is built from the atmosphere the beam actually came
# through, and the aerosol pair waits for the round that can afford both halves.
#
# WHAT IT WOULD COST, measured rather than guessed: this file was rendered with
# that pair in, at tau_a(550) = 0.10, Angstrom 1.0, single-scattering albedo
# 0.95, half of the coarse mode's scattering in a 2.0 um diffraction peak. It
# put a peak radiance of 72 into a 3.4 deg lobe and 15 into a 13.5 deg one, and
# on the picture it moved the mirror band's REFLECTED median from 0.16 to 4.04
# -- past this file's own white point of 11.2 once the disc's glints are added
# on top -- and took the far water's mean luminance to 245 of 255 with 98% of it
# over 200. A frame shot along the sun's azimuth cannot hold both a hazy sky and
# a legible bed, which is a statement about the reference photograph's weather
# as much as about this renderer.

# sky() multiplies the WHOLE environment by 1.15, and the background wants it --
# it is what makes what sky() returns agree with SKY_AMB. The amplitudes below
# are absolute RADIANCES and must not be scaled a second time, so each carries
# 1/1.15 and the product is the derived peak exactly.
_UNSCALE = 1.0 / 1.15
SKY_LOBE = ((_UNSCALE, N_DISC, L_SUN),             # the disc
            (_UNSCALE, N_AURE, L_AURE))            # the Rayleigh aureole


def _lobe_shape(n, cov):
    """One cos^n lobe of the environment, convolved with the reflection ellipse
    that the UNRESOLVED slope variance puts on the mirror direction.

    Two Gaussians convolve to a Gaussian whose covariance is the sum and whose
    INTEGRAL is unchanged, so the peak falls by sqrt(det Q_0 / det Q). Writing
    the widened lobe back as cos^(n_eff) rather than as exp(-n_eff th^2 / 2)
    costs nothing and buys the one property that matters here: at cov = None it
    is EXACTLY the expression this file had before, so the unfiltered path is
    bit-for-bit the old one and the sky behind the pool never moves.

    n_eff is directional -- 1 / (u_hat^T Q u_hat), the variance of the summed
    Gaussian along the direction of the offset to the sun -- which is how the
    anisotropy survives. WIND is a 45 deg spread about the wind azimuth and the
    wake is directional, so what the filter removes is a Cox-Munk ellipse and a
    lobe widened by its trace would be visibly wrong across the wind. On the
    axis (offset zero) every direction gives cos^n = 1 and only the peak factor
    is doing anything, so the fallback there is the mean variance."""
    if cov is None:
        return 1.0, n
    u1, u2, c11, c12, c22 = cov
    q11 = 1.0 / n + c11
    q22 = 1.0 / n + c22
    det = np.maximum(q11 * q22 - c12 * c12, 1e-30)
    g = (1.0 / n) / np.sqrt(det)
    r2 = u1 * u1 + u2 * u2
    w = np.where(r2 > 1e-16,
                 (u1 * u1 * q11 + 2.0 * u1 * u2 * c12 + u2 * u2 * q22)
                 / np.maximum(r2, 1e-16),
                 0.5 * (q11 + q22))
    return g, 1.0 / np.maximum(w, 1e-12)


def sky(dx, dy, dz, cov=None):
    t = np.clip(dz, 0, 1)[:, None] ** .55
    col = SKY_HOR[None] * (1 - t) + SKY_TOP[None] * t
    cs = np.clip(dx * SUN_DIR[0] + dy * SUN_DIR[1] + dz * SUN_DIR[2], 0, 1)
    for amp, n, c in SKY_LOBE:
        g, ne = _lobe_shape(n, cov)
        if cov is None:
            col = col + c[None] * amp * (cs ** ne)[:, None]
        else:
            col = col + c[None] * amp * (g * cs ** ne)[:, None]
    return col * 1.15


print("sky lobes: per-axis sigma %s deg -- these are the angular scales the "
      "reflection ellipse has to be compared against"
      % ", ".join("%.2f" % np.degrees(1.0 / np.sqrt(n)) for _, n, _ in SKY_LOBE))

# --- THE SUN AS A SOURCE, AUDITED AGAINST THE ENVIRONMENT THAT STANDS IN FOR IT
# The audit that priced the guess, now run against the derivation. It stays
# because it is the check, not the finding: every quantity it prints is computed
# from SKY_LOBE as shipped, so if a later round moves an amplitude the ratios
# move with it and say so.
#
# `shade` uses SUN_COL as E_n/pi -- a Lambertian bed of albedo rho lit at
# incidence cos_i comes out at rho*SUN_COL*cos_i, and rho*E/pi is the definition
# -- so E_n = pi*SUN_COL. `sky` returns RADIANCE in the same units, which is
# checkable independently: a uniform sky of radiance L gives E = pi*L, so the
# diffuse SKY_AMB and the SKY_HOR/SKY_TOP that sky() returns are the same
# quantity, and they agree to 4% in green. Both scales are therefore pinned, and
# the sun's own radiance follows with nothing left free:
#     L_sun = E_n / Omega_sun = pi * SUN_COL / (pi (0.53 deg / 2)^2)
# The environment's three lobes are then measurable against it, in peak and in
# flux (a cos^n lobe integrates to 2 pi/(n+1) sr over the hemisphere).
_lobe_flux = sum(amp * c * 1.15 * 2 * np.pi / (n + 1) for amp, n, c in SKY_LOBE)
_disc_pk = SKY_LOBE[0][0] * SKY_LOBE[0][2][1] * 1.15
print("  the sun's own radiance is pi*SUN_COL/Omega_sun = %.3g (green) in those "
      "units; the disc lobe's PEAK is %.4g, so the reflected sun is %.3fx the "
      "physical one, and cos^%.0f covers %.3g sr against the disc's %.3g -- "
      "%.3fx its width"
      % (L_SUN[1], _disc_pk, L_SUN[1] / _disc_pk, SKY_LOBE[0][1],
         2 * np.pi / (SKY_LOBE[0][1] + 1), OMEGA_SUN,
         (2 * np.pi / (SKY_LOBE[0][1] + 1)) / OMEGA_SUN))
print("  in FLUX, which is what a reflection actually integrates: the lobes "
      "together carry %.3g against a direct beam of pi*SUN_COL = %.3g, a factor "
      "%.3f. The disc carries the beam EXACTLY and the %.1f%% over it is the "
      "Rayleigh forward excess, which is scattered out of the same beam -- so "
      "the environment now conserves the sun instead of losing 97%% of it."
      % (_lobe_flux[1], E_SUN[1], _lobe_flux[1] / E_SUN[1],
         100 * (_lobe_flux[1] / E_SUN[1] - 1.)))
print("  lobe        per-axis sigma      Omega (sr)     peak L        flux "
      "(green, against a beam of %.1f)" % E_SUN[1])
for _nm, (_amp, _n, _c) in zip(("disc    ", "aureole ", "lobe 3  "), SKY_LOBE):
    print("    %s  %8.3f deg   %10.3g   %10.4g   %8.3g"
          % (_nm, np.degrees(1. / np.sqrt(_n)), 2 * np.pi / (_n + 1),
             _amp * _c[1] * 1.15, _amp * _c[1] * 1.15 * 2 * np.pi / (_n + 1)))
# The aureole against a quantity that is MEASURED for this exact geometry. The
# circumsolar ratio is the fraction of the beam-plus-circumsolar flux arriving
# outside the disc but inside a 3.2 deg acceptance: ~0.05 for a clear sky and
# several times that for haze. A Rayleigh atmosphere cannot reach it, and that
# is the honest reading -- the missing part is the aerosol diffraction peak this
# file cannot afford, not an amplitude waiting to be raised.
_csr_in = 1. - np.cos(np.deg2rad(3.2)) ** (N_AURE + 1.)
_lf = _lobe_flux[1] - E_SUN[1]
print("  aureole cross-check: %.1f%% of the Rayleigh lobe's flux falls inside "
      "the 3.2 deg circumsolar acceptance, so it reads CSR = %.4f against the "
      "~0.05 measured for a clear sky -- %.0fx short, and ALL of that shortfall "
      "is the aerosol diffraction peak derived to zero above. The 3.2 deg "
      "acceptance is 24 times this lobe's own %0.f deg width, which is the same "
      "statement seen from the angular side: a clean sky has no compact aureole."
      % (100 * _csr_in, _lf * _csr_in / (_lf * _csr_in + E_SUN[1]),
         0.05 / max(_lf * _csr_in / (_lf * _csr_in + E_SUN[1]), 1e-12),
         np.degrees(1. / np.sqrt(N_AURE))))


# --------------------------------------- the removed variance becomes a lobe
# WHAT THIS FILE DID NOT HAVE, and had to grow before the footprint filter
# could be turned on at all. The surface was a MIRROR: one normal per sample,
# one reflected ray, one lookup into `sky`. There was no microfacet lobe to
# feed, so `field.slope_var_points`' returned tensor had nowhere to go, and
# narrowing the slope field without it is the exact failure the chapter's
# "Distance and filtering" opens with -- the far water stops carrying slope
# variance, its specular response collapses toward the mirror, and it reads as
# shrink-wrapped perspex. Filtering and this term are one change, not two.
#
# THE DERIVATION, because the factors of two and the cos(theta_v) are the whole
# content. Let the resolved normal be n and the unresolved slope be a zero-mean
# Gaussian 2-vector d with covariance SIGMA (that IS the returned tensor). To
# first order the normal tilts by -d, and R = 2(n.v)n - v gives
#     dR = 2(dn.v) n + 2(n.v) dn.
# Put the incidence plane in x-z with n = z and v = (sin tv, 0, cos tv):
#   * d along the view azimuth (IN the plane): dR = -2 d_p e_hat -- the full
#     factor two, because the tilt swings both the normal and the incidence
#     angle;
#   * d across it: dR = -2 cos(tv) d_q s_hat -- foreshortened, because an
#     out-of-plane tilt only rotates the ray about the view direction.
# So with J = diag(-2, -2 cos tv) in the frame (in-plane, across-plane),
# C = J SIGMA' J^T, and the reflection ellipse is not similar to the slope
# ellipse: it is stretched along the view azimuth by 1/cos(tv). At this
# camera's 33 deg that is a 1.8x anisotropy the slope tensor never had, which
# is a second reason a scalar roughness would be wrong here.
#
# e_hat and s_hat are the two directions perpendicular to R -- s_hat normal to
# the incidence plane, e_hat completing it -- so the offset to the sun is just
# its two components in that frame and no angles are ever formed.
def _refl_ellipse(dvec, nx_, ny_, nz_, ndv_, rx_, ry_, rz_, vxx, vyy, vxy):
    """(u1, u2, C11, C12, C22, sigma_v^2): the offset from the reflected ray to
    the sun, the angular covariance the unresolved slope puts on that ray -- both
    in the frame perpendicular to R -- and the one-direction slope variance along
    the view azimuth, which is what the Fresnel term below needs."""
    vx_, vy_, vz_ = -dvec[:, 0], -dvec[:, 1], -dvec[:, 2]
    # the incidence plane's normal, then made perpendicular to R as well: rz_ is
    # folded to |rz_| upstream for the sky lookup, and on those few rays s0 is
    # not already perpendicular to the folded ray.
    s0x = vy_ * nz_ - vz_ * ny_
    s0y = vz_ * nx_ - vx_ * nz_
    s0z = vx_ * ny_ - vy_ * nx_
    d = s0x * rx_ + s0y * ry_ + s0z * rz_
    s0x, s0y, s0z = s0x - d * rx_, s0y - d * ry_, s0z - d * rz_
    inv = 1.0 / np.maximum(np.sqrt(s0x ** 2 + s0y ** 2 + s0z ** 2), 1e-9)
    sx, sy, sz = s0x * inv, s0y * inv, s0z * inv
    ex, ey, ez = ry_ * sz - rz_ * sy, rz_ * sx - rx_ * sz, rx_ * sy - ry_ * sx
    # the slope tensor rotated into (along the view azimuth, across it). q_hat is
    # (py, -px) rather than (-py, px) so that it points along s_hat: with
    # v = (sin tv, 0, cos tv) the incidence normal is -y, and the sign of the
    # cross term is the only place that choice shows.
    ph = np.maximum(np.hypot(vx_, vy_), 1e-9)
    px, py = vx_ / ph, vy_ / ph
    a = px * px * vxx + 2.0 * px * py * vxy + py * py * vyy
    b = py * py * vxx - 2.0 * px * py * vxy + px * px * vyy
    cr = px * py * (vxx - vyy) + (py * py - px * px) * vxy
    c11 = 4.0 * a
    c12 = 4.0 * ndv_ * cr
    c22 = 4.0 * ndv_ * ndv_ * b
    u1 = SUN_DIR[0] * ex + SUN_DIR[1] * ey + SUN_DIR[2] * ez
    u2 = SUN_DIR[0] * sx + SUN_DIR[1] * sy + SUN_DIR[2] * sz
    return u1, u2, c11, c12, c22, a


# Cause two on the chapter's own list, and the other half of what makes the
# filter safe: the Fresnel equations are derived for a SMOOTH interface, and on a
# rough one the microfacets mask each other at grazing incidence. Ship the smooth
# curve on a low-variance distant surface and the far band goes to a near-100%
# mirror -- the chrome-dome reading, the same defect as the plastic one seen
# from the reflection side rather than the lobe side. Bruneton, Neyret &
# Holzschuch (2010) fit the correction for sigma_v < 0.5:
#     F = R + (1-R)(1-cos tv)^5 exp(-2.69 sigma_v) / (1 + 22.7 sigma_v^1.5)
# and sigma_v is the ONE-DIRECTION slope rms along the view azimuth, not the
# total -- the `a` component above, in the file's own tensor. Two constants,
# both theirs, neither fitted here.
#
# It is fed the UNRESOLVED variance only, and that is the consistent reading for
# a surface that is half resolved and half statistical: the traced normal is the
# facet the pixel is actually looking at, so what still needs masking is the
# sub-pixel remainder. It therefore goes to 1 as the footprint goes to zero and
# the near water's Fresnel is untouched, which is the same boundary condition
# the lobe widening has.
#
# The base is now the EXACT Fresnel curve, not Schlick. Bruneton's factor `r`
# multiplies the interface's grazing RISE above F0 -- which is what microfacet
# masking attenuates -- so the composition is
#     F = F0 + (F_exact(cos tv) - F0) * r
# instead of F0 + (1 - F0)(1 - cos tv)^5 * r. `(1 - cos tv)^5 (1 - F0)` was only
# ever Schlick's model OF that rise, so this substitutes the thing for the model
# of it and changes nothing else. Both boundary conditions survive intact: r -> 1
# (zero unresolved variance) gives exactly F_exact, which is now the exact
# smooth-interface answer rather than one 14% wrong at 79 deg; r -> 0 gives F0.
def _fresnel_rough(ndv_, sv2):
    sv = np.sqrt(np.maximum(sv2, 0.0))
    r = (np.exp(-2.69 * sv) / (1.0 + 22.7 * sv ** 1.5))[..., None]
    return F0 + (fresnel(ndv_) - F0) * r


_VN = rng.random((256, 256))


def vnoise(x, y):
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - xi, y - yi
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    g = lambda a, b: _VN[(yi + b) & 255, (xi + a) & 255]
    return ((g(0, 0) * (1 - fx) + g(1, 0) * fx) * (1 - fy) +
            (g(0, 1) * (1 - fx) + g(1, 1) * fx) * fy)


def vnoise_d(x, y):
    """Same field, with its analytic gradient -- the paving needs slopes, not
    values: at a 21 degree sun the relief is carried by N.L, not by albedo."""
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - xi, y - yi
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    dux, duy = 6 * fx * (1 - fx), 6 * fy * (1 - fy)
    g = lambda a, b: _VN[(yi + b) & 255, (xi + a) & 255]
    a00, a10, a01, a11 = g(0, 0), g(1, 0), g(0, 1), g(1, 1)
    k1, k2 = a10 - a00, a01 - a00
    k3 = a00 - a10 - a01 + a11
    return (a00 + k1 * ux + k2 * uy + k3 * ux * uy,
            (k1 + k3 * uy) * dux, (k2 + k3 * ux) * duy)


# --------------------------------------------------------------------------- the pool edge
# The single thing this file used to get wrong. The water was a rectangle test
# against a deck plane 55 mm up, so the two met along an aliased boolean line and
# the pool read as a decal. It is replaced here by the actual section of a pool
# edge, traced as a height field: wall, coping bedded on it and OVERHANGING its
# face, bullnose rolled over the overhang, water 75 mm below the coping top.
pool_s = pool_sdf              # the shape enters through ONE function; see the top
pool_grad = pool_sdf_grad


def edge_z(s):
    d = np.clip(SBUL - s, 0., BULR)
    return np.where(s >= SBUL, ZD, ZCEN + np.sqrt(np.maximum(BULR * BULR - d * d, 0.)))


def _hash(a, b, k=0.):
    v = np.sin(a * 127.1 + b * 311.7 + k * 74.7) * 43758.5453
    return v - np.floor(v)


def _run(x, y):
    """Position along the coping course, and which of the four sides it is on."""
    gx, gy, e = pool_grad(x, y)
    return np.where(e, y, x), np.where(e, np.where(gx > 0, 0., 1.),
                                       np.where(gy > 0, 2., 3.)), gx, gy, e


def lip_wobble(x, y):
    """Coping stones are LAID, not extruded. Each sits a couple of millimetres
    proud or shy of its neighbour and its arris is worn unevenly, so the line
    where water meets stone is never straight. Amplitude 4 mm, which is a third
    of a pixel at the far coping and four pixels at the near one -- and at the
    near one a mathematically straight, stair-stepped waterline was the loudest
    synthetic tell left in the frame. Physical, and it dithers the edge."""
    a, sd, _, _, _ = _run(x, y)
    k = np.floor((a + .19 * sd) / .55)
    return (.0040 * (_hash(k, sd, 5.7) - .5) * 2.
            + .0026 * (vnoise(a * 11., sd * 7.3 + .5) - .5) * 2.)


def pool_se(x, y):
    return pool_s(x, y) + lip_wobble(x, y)


def gh(x, y):
    s = pool_se(x, y)
    return np.where(s < SLIP, 0.0, edge_z(s))


# --------------------------------------------------------- caustic light OUT of the pool
# The other half of the WBOUNCE term. The bed is a bright diffuse reflector
# carrying the sun's net; that radiance hits the UNDERSIDE of the same wavy
# surface, and the surface lenses it on the way out exactly as on the way in. So
# what leaves the pool is not a uniform teal glow -- it is a focused, moving
# pattern, spatially coherent with the caustics on the bed because it is the same
# wave field and the same bed map, read along the reverse path.
#
# The path is traced, not invented: from a point on the stone, aim back at the
# water, refract INTO it with the real field.py normal at that point, trace to
# the bed with the same scene_hit, read the same bed_img. Fresnel on that entry
# is by reciprocity the transmittance the light actually had leaving, and it is
# what kills the near-grazing contributions from far out in the basin.
#
# WHAT CAN SEE THE WATER AT ALL. A horizontal stone face 75 mm ABOVE the water
# plane cannot: every direction toward the water is below its horizon, N.w < 0.
# Only faces that tip toward the pool see it -- the bullnose, the poolward flank
# of every joint groove, and the poolward half of the stone's own micro-relief.
# So the receiver normal used here is the POOLWARD HORIZONTAL one, and what the
# flat top of the coping gets is only the sub-pixel-facet share of that (the
# 0.10 below, which stays a `?`). The falloff is no longer a guessed exponential.
# The capillary scale, hoisted here from the water-shading block below because
# the liner band's wet foot is built in this section and needs it. The long
# derivation stays where the meniscus itself is applied to the water.
CAP_A = np.sqrt(SIGMA_W / (1000.0 * 9.81))          # capillary length, 2.72 mm
# ? THE CONTACT ANGLE IS THE ONE FREE NUMBER IN THE WHOLE FILLET, and it is
# ? unmeasured. It sets the tilt AT the wall, phi_w = 90 - theta_c, and through
# ? that both the climb h = a sqrt(2(1 - sin theta_c)) and the top of the range
# ? the specular integral below sweeps. 0 -- perfect wetting -- is what this file
# ? has assumed since the climb was first written, and it is kept here so that
# ? MENIS_H and everything downstream of it (WETTOP, the wet foot) do not move.
# ? A clean PVC sheet is nearer 80 deg; a liner in service, permanently wetted
# ? and biofilmed, is nearer 0, and nobody has measured THIS one. The
# ? sensitivity is printed instead of being hidden, here and at the line itself.
THETA_C = 0.0
PHI_W = np.pi / 2 - THETA_C                         # ? surface tilt at the wall
MENIS_H = CAP_A * np.sqrt(2.0 * (1.0 - np.sin(THETA_C)))    # ? climb, at THETA_C
MENIS_W = 2.0 * CAP_A                               # fillet reach, ~2 a
print("meniscus: capillary length %.2f mm, climb %.2f mm at contact angle "
      "%.0f deg (%s mm at 0/30/60 deg -- ? the angle is unmeasured), tilt at "
      "the wall %.0f deg, fillet %.1f mm wide"
      % (1000 * CAP_A, 1000 * MENIS_H, np.degrees(THETA_C),
         " / ".join("%.2f" % (1000 * CAP_A * np.sqrt(2 * (1 - np.sin(np.deg2rad(t)))))
                    for t in (0, 30, 60)),
         np.degrees(PHI_W), 1000 * MENIS_W))

DECK_S = np.array([SLIP, 0.02, 0.06, 0.14, 0.30, 0.55, 0.95])
DECK_DA = 0.005                      # 5 mm along the run; the pattern's own
DECK_NA = [int(round((Y1 - Y0) / DECK_DA))] * 2 + \
          [int(round((X1 - X0) / DECK_DA))] * 2      # finest scale is ~70 mm
_DG = [(1., 0., 0., 1., X1, None), (-1., 0., 0., 1., X0, None),
       (0., 1., 1., 0., None, Y1), (0., -1., 1., 0., None, Y0)]
_NRHO, _NPHI = 12, 7
_RHO = np.exp(np.linspace(np.log(0.010), np.log(6.0), _NRHO))
_PHI = np.linspace(-np.deg2rad(75.), np.deg2rad(75.), _NPHI)


def _gather(flat, samples):
    """Irradiance on a poolward-facing facet from the water surface.
    Polar quadrature over the water: for a facet at height qz above the still
    plane and a surface point at horizontal distance rho and bearing phi off the
    inward normal, R^2 = rho^2 + qz^2, the incoming direction carries
    (N.w) = rho cos(phi)/R and dOmega = (qz/R) dA/R^2, so the weight is
    rho cos(phi) qz / R^4 -- a 1/s falloff before Fresnel, and steeper after it,
    which is the 'near-grazing exit from a source of finite extent' the pattern
    is supposed to have.

    `samples` is a list of (s, qz, rho_grid): where the facet sits back from the
    lip, how high it stands over the still water, and the radial quadrature to
    use. The stone facets are one family of those (s varies, qz = edge_z(s)) and
    the liner band is another (s pinned at the lip, qz sweeping the band's own
    height) -- the SAME estimator, which is the point: the band is not a new
    light transport, it is the receiver this gather was built for, at last
    pointed at the surface that shows it best."""
    out = []
    for sd in range(4):
        gx, gy, lx, ly, fx, fy = _DG[sd]
        a = (np.arange(DECK_NA[sd]) + .5) * DECK_DA + (Y0 if sd < 2 else X0)
        acc = np.zeros((len(samples), DECK_NA[sd], 3))
        for si, (s, qz, rgrid) in enumerate(samples):
            bx = (fx + gx * s) if fx is not None else a
            by = (fy + gy * s) if fy is not None else a
            bx = np.broadcast_to(np.atleast_1d(bx), a.shape).astype(np.float64)
            by = np.broadcast_to(np.atleast_1d(by), a.shape).astype(np.float64)
            for ph in _PHI:
                cp, sp = np.cos(ph), np.sin(ph)
                r0 = max((s - SLIP) / cp, 1e-3)
                rho = rgrid[rgrid > r0]
                if not rho.size:
                    rho = np.array([r0 * 1.05])
                dln = np.log(rgrid[-1] / rgrid[0]) / (len(rgrid) - 1)
                dphi = (_PHI[-1] - _PHI[0]) / (_NPHI - 1)
                for rr in rho:
                    px = bx - gx * rr * cp + lx * rr * sp
                    py = by - gy * rr * cp + ly * rr * sp
                    ok = pool_sdf(px, py) < SLIP
                    if not ok.any():
                        continue
                    R = np.hypot(rr, qz)
                    # direction from the facet DOWN to the water point
                    wx, wy, wz = (px - bx) / R, (py - by) / R, -qz / R
                    if flat:
                        nx_, ny_, nz_ = np.zeros_like(px), np.zeros_like(px), np.ones_like(px)
                    else:
                        nx_, ny_, nz_ = normal_from_grad(*grad_points(px, py))
                    cosi = -(wx * nx_ + wy * ny_ + wz * nz_)
                    # eta = 1/n < 1: this facet looks DOWN through the surface
                    # from the air, so there is no TIR branch to take.
                    tx, ty, tz = refract(wx, wy, wz, nx_, ny_, nz_, 1.0 / IOR[1])
                    sid, u, v, sm, _ = scene_hit(px, py, tx, ty, tz)
                    col = np.zeros((len(px), 3))
                    m = sid == 0
                    if m.any():
                        col[m] = sample(bed_img['mono'], u[m], v[m], X0, X1, Y0, Y1)
                    for wi, sv in enumerate((1, 2, 3, 4)):
                        m = sid == sv
                        if m.any():
                            aa, bb = (Y0, Y1) if sv <= 2 else (X0, X1)
                            col[m] = sample(wall_img['mono'][wi], u[m], v[m],
                                            aa, bb, -DEPTH, 0.)
                    col = col * np.exp(-ABS[None] * sm[:, None])
                    T = 1.0 - fresnel(np.clip(cosi, 0, 1))    # exact, not Schlick
                    w = rr * cp * qz / R ** 4 * (rr * rr * dln * dphi)
                    acc[si] += np.where(ok[:, None], col * T * w, 0.0)
        out.append(acc)
    return out


DECK_SAMP = [(float(s), float(edge_z(np.array([s]))[0]), _RHO) for s in DECK_S]
# --- and the same gather aimed at the liner band -----------------------------
# The band is a poolward-facing vertical strip standing ON the water, so it is
# the receiver above with s pinned at the lip and qz swept over the band's own
# 100 mm. Two things make it a separate family rather than two more DECK_S rows:
#   * the RADIAL GRID has to follow the height. The integrand rho^2 cos(phi) qz
#     / R^4 peaks at rho = qz, so a facet 6 mm up is lit almost entirely by
#     water within a centimetre of it, and _RHO's fixed 10 mm floor would miss
#     the whole peak. Each band height therefore gets its own log grid from
#     0.25 qz out to 4 m, the basin's own width.
#   * that same shift is the PHYSICS the bar is pointing at. The flat-water form
#     factor is scale invariant -- a vertical facet over an infinite plane
#     collects the same irradiance at any height -- so the band is not brighter
#     than the coping because it catches more light. It is more LEGIBLE because
#     the patch of surface it integrates shrinks with height: at 6 mm it reads a
#     centimetre of water and resolves single caustic bands; at 100 mm it reads
#     a decimetre; the coping at 300 mm back and 132 mm up reads half a metre
#     and averages the net away. The contrast printed below is that statement
#     measured, height by height.
BAND_Z = np.exp(np.linspace(np.log(0.006), np.log(ZLIP), 4))
_NRHO_B = 14
BAND_SAMP = [(SLIP, float(z),
              np.exp(np.linspace(np.log(0.25 * z), np.log(4.0), _NRHO_B)))
             for z in BAND_Z]
print("water-out pass: %d stone facets x %d water samples, plus %d band facets "
      "x %d" % (sum(DECK_NA) * len(DECK_S), _NRHO * _NPHI,
                sum(DECK_NA) * len(BAND_Z), _NRHO_B * _NPHI), flush=True)
DECK = _gather(False, DECK_SAMP)
DECK0 = _gather(True, DECK_SAMP)
BANDG = _gather(False, BAND_SAMP)
BANDG0 = _gather(True, BAND_SAMP)
_fall = np.array([DECK0[2][si].mean() for si in range(len(DECK_S))])
_fall /= _fall[0]
print("  water-out falloff off the lip: " +
      "  ".join("%.0fmm:%.2f" % (1000 * s, f) for s, f in zip(DECK_S, _fall)))
_pat = np.array([np.std(DECK[2][si, :, 1] / np.maximum(DECK0[2][si, :, 1], 1e-12))
                 for si in range(len(DECK_S))])
print("  pattern contrast (rms/mean of the lensed / flat ratio): " +
      "  ".join("%.2f" % p for p in _pat))
# the flat gather up the band, against the scale-invariance claim above: a
# vertical facet over an INFINITE flat plane collects the same irradiance at
# every height, so any departure here is the basin's finite width plus the
# quadrature, and it is reported rather than assumed away.
_bfall = np.array([BANDG0[2][si, :, 1].mean() for si in range(len(BAND_Z))])
print("  band, flat-water irradiance vs height (scale invariance says 1.00): " +
      "  ".join("%.0fmm:%.2f" % (1000 * z, f / _bfall[-1])
                for z, f in zip(BAND_Z, _bfall)))
# ...and the claim B2b actually makes -- that this band carries the pattern
# BETTER than the coping does -- in the coping's own units, so the two lines can
# be read against each other directly. Same estimator, same wall, same statistic.
_bpat = np.array([np.std(BANDG[2][si, :, 1] / np.maximum(BANDG0[2][si, :, 1], 1e-12))
                  for si in range(len(BAND_Z))])
print("  band, pattern contrast in the SAME units as the line above: " +
      "  ".join("%.0fmm:%.2f" % (1000 * z, p) for z, p in zip(BAND_Z, _bpat))
      + "  -- against %.2f for the stone at the lip and %.2f half a metre back"
      % (_pat[0], _pat[5]))


def _map_at(G, G0, lev, levs, along, side, ref):
    """Bilinear lookup of a water-out gather in (level, along). Returns the
    LENSED/FLAT ratio -- mean one by construction, so it modulates a DC instead
    of adding energy to it -- and the flat gather relative to its value at level
    `ref`, which is the falloff."""
    out = np.ones((len(along), 3)); fal = np.ones(len(along))
    fs = np.interp(np.clip(lev, levs[0], levs[-1]), levs, np.arange(len(levs)))
    i0 = np.clip(fs.astype(np.int64), 0, len(levs) - 2); ft = (fs - i0)[:, None]
    for sd in range(4):
        m = side == sd
        if not m.any():
            continue
        fa = np.clip((along[m] - (Y0 if sd < 2 else X0)) / DECK_DA - .5,
                     0, DECK_NA[sd] - 1.001)
        ja = fa.astype(np.int64); fj = (fa - ja)[:, None]
        A, B = G[sd], G0[sd]
        j0, k0 = i0[m], ja
        def g(arr):
            lo = arr[j0, k0] * (1 - fj) + arr[j0, k0 + 1] * fj
            hi = arr[j0 + 1, k0] * (1 - fj) + arr[j0 + 1, k0 + 1] * fj
            return lo * (1 - ft[m]) + hi * ft[m]
        num, den = g(A), g(B)
        # ? clipped at 4x: far out on the deck the flat reference is nearly zero
        # ? and the ratio is quadrature noise, not lensing. It is multiplied by a
        # ? falloff of order 0.01 there, so the clip changes nothing visible.
        out[m] = np.clip(num / np.maximum(den, 1e-12), 0., 4.)
        fal[m] = den[:, 1] / max(G0[sd][ref, :, 1].mean(), 1e-12)
    return out, fal


def deck_water(along, side, s):
    """Bilinear lookup of the water-out map: pattern ratio, and derived falloff."""
    return _map_at(DECK, DECK0, s, DECK_S, along, side, 0)


def band_water(along, side, z):
    """The same, up the liner band: `z` is height over the still waterline."""
    return _map_at(BANDG, BANDG0, z, BAND_Z, along, side, len(BAND_Z) - 1)


# --- WHERE THE WATER ACTUALLY MEETS THE WALL ---------------------------------
# The sixth reference photograph shows the waterline against the WALL soft, wet
# and undulating. That does NOT reverse bar section B2, and reading it as a
# contradiction is the mistake B3 was written to prevent: B2 is the COPING'S
# ARRIS, cut stone seen from above, and it stays hard. This is the WALL'S
# waterline, a different edge, and B3 already puts the meniscus on it.
#
# render.py has no height field -- field.py answers slopes, not elevations --
# but along a straight wall it does not need one. The surface elevation along
# the wall is the LINE INTEGRAL of the along-wall slope component, which is
# exact up to an additive constant, and the constant is the mean water level.
# Integrating a zero-mean field is a random walk, so the result is high-passed
# at 1 m: that removes only frequencies the field has no energy at (its longest
# carrier is 0.53 m) and it kills the walk. Nothing is invented here -- the
# wobble is the same wave field the caustics are, read along one line.
def _waterline():
    out = []
    for sd in range(4):
        gx, gy, lx, ly, fx, fy = _DG[sd]
        a = (np.arange(DECK_NA[sd]) + .5) * DECK_DA + (Y0 if sd < 2 else X0)
        px = (fx + gx * (SLIP - .030)) if fx is not None else a
        py = (fy + gy * (SLIP - .030)) if fy is not None else a
        px = np.broadcast_to(np.atleast_1d(px), a.shape).astype(np.float64)
        py = np.broadcast_to(np.atleast_1d(py), a.shape).astype(np.float64)
        sx, sy = grad_points(px, py)
        eta = np.cumsum((sx * lx + sy * ly) * DECK_DA)
        out.append(_hipass(eta - eta.mean(), 0.5 / DECK_DA))
    return out


WLINE = _waterline()
ETA_RMS = float(np.mean([w.std() for w in WLINE]))
# How far up the liner is still wet: the meniscus climb plus a couple of sigma
# of that wobble, which is everything the surface has recently covered. Both
# terms are derived, so the wet band's HEIGHT is a prediction and not a look --
# and the prediction is that on a still pool it is under a centimetre.
WETTOP = MENIS_H + 2.0 * ETA_RMS
print("waterline on the wall, reconstructed by integrating the along-wall slope: "
      "rms %.2f mm, p2p %.2f mm -- against a meniscus climb of %.2f mm, so the "
      "wobble and the fillet are the same size and the line is soft rather than "
      "cut; the liner is wet to %.1f mm"
      % (1000 * ETA_RMS,
         1000 * float(np.mean([w.max() - w.min() for w in WLINE])),
         1000 * MENIS_H, 1000 * WETTOP))


def waterline(along, side):
    """Local surface elevation where the water meets the wall, metres."""
    out = np.zeros(len(along))
    for sd in range(4):
        m = side == sd
        if not m.any():
            continue
        fa = np.clip((along[m] - (Y0 if sd < 2 else X0)) / DECK_DA - .5,
                     0, DECK_NA[sd] - 1.001)
        ja = fa.astype(np.int64); fj = fa - ja
        out[m] = WLINE[sd][ja] * (1 - fj) + WLINE[sd][ja + 1] * fj
    return out


# --- WET LINER, DERIVED RATHER THAN DIALLED ----------------------------------
# A film of water on a NON-POROUS substrate darkens it by a mechanism with no
# free parameter: light crosses the air/water interface twice, and between the
# crossings it is trapped by total internal reflection. With R_EXT the diffuse
# external reflectance of that interface -- integrated below from THIS FILE'S
# own per-channel Fresnel over a cosine-weighted hemisphere, so no constant
# enters -- and R_INT = 1 - (1 - R_EXT)/n^2 by reciprocity, a substrate of dry
# albedo `a` reads
#       a_wet = R_EXT + (1 - R_EXT)(1 - R_INT) a / (1 - a R_INT)
# The wet band at the foot of the blue is therefore a measured fraction of the
# dry one, and it is printed rather than chosen.
_wmu = ((np.arange(512) + .5) / 512.)[:, None]
_wct = np.sqrt(np.maximum(1. - (1. - _wmu ** 2) / IOR[None] ** 2, 0.))
_wrs = ((_wmu - IOR[None] * _wct) / (_wmu + IOR[None] * _wct)) ** 2
_wrp = ((IOR[None] * _wmu - _wct) / (IOR[None] * _wmu + _wct)) ** 2
R_EXT = (2. * _wmu * .5 * (_wrs + _wrp)).mean(0)
R_INT = 1. - (1. - R_EXT) / IOR ** 2


def wet_albedo(a):
    return R_EXT[None] + (1. - R_EXT[None]) * (1. - R_INT[None]) * a / (
        1. - a * R_INT[None])


print("wet liner: diffuse Fresnel R_ext %s, R_int %s (1 - (1-R_ext)/n^2), so a "
      "wetted liner reads %s of its dry albedo" %
      (np.round(R_EXT, 4), np.round(R_INT, 4),
       np.round(wet_albedo(0.74 * LINER_TINT[None])[0] / (0.74 * LINER_TINT), 3)))


def _groove(c, per, hw, dep):
    """A joint every `per` metres. A 5 mm groove under a 21 degree sun is not a
    drawn line: it is one face that catches the sun and one that cannot."""
    f = (c / per) % 1.0
    d = np.minimum(f, 1 - f) * per
    return (-dep * np.clip(1 - d / hw, 0, 1),
            np.where(d < hw, dep / hw * np.where(f < .5, 1., -1.), 0.),
            np.clip(1 - d / hw, 0, 1), np.clip(1 - d / .050, 0, 1))


def _notch(c, c0, hw, dep):
    d = np.abs(c - c0)
    return (-dep * np.clip(1 - d / hw, 0, 1),
            np.where(d < hw, dep / hw * np.sign(c - c0), 0.),
            np.clip(1 - d / hw, 0, 1), np.clip(1 - d / .050, 0, 1))


def _stone(x, y, s, vdir, fp):
    """Coping course and terrace. In this frame it is a border, so it gets what a
    border needs and nothing else: stone that changes stone to stone, joints with
    a groove rather than a line, and the splash-damp band every coping carries
    within a hand's width of the water -- darker, and glossy where the stone is
    matt. No garden, no props."""
    along, side, gx, gy, ex = _run(x, y)
    cop = s < COPW

    # --- joints: coping runs across the course, the terrace is a 0.92 x 0.61 field
    ja, dja, ga, wa = _groove(along + .19 * side, .55, .009, .0050)
    jn, djn, gn, wn = _notch(s, COPW, .009, .0050)
    row = np.floor(y / .61)
    jx, djx, gxj, wxj = _groove(x + .46 * (row % 2.), .92, .008, .0045)
    jy, djy, gyj, wyj = _groove(y, .61, .008, .0045)
    dzx = np.where(cop, np.where(ex, 0., dja) + djn * gx, djx)
    dzy = np.where(cop, np.where(ex, dja, 0.) + djn * gy, djy)
    jm = np.where(cop, np.maximum(ga, gn), np.maximum(gxj, gyj))
    jw = np.where(cop, np.maximum(wa, wn), np.maximum(wxj, wyj))

    # --- micro relief, faded out once an octave is finer than the pixel footprint
    n1, d1x, d1y = vnoise_d(x * 1.9, y * 1.9)
    n2, d2x, d2y = vnoise_d(x * 8.5 + 11., y * 8.5 + 3.)
    n3, d3x, d3y = vnoise_d(x * 33. + 5., y * 33. + 7.)
    n4, d4x, d4y = vnoise_d(x * 128. + 19., y * 128. + 23.)
    n5, d5x, d5y = vnoise_d(x * 430. + 2., y * 430. + 8.)
    w2 = 1. / (1. + (2.6 * fp * 8.5) ** 2)
    w3 = 1. / (1. + (2.6 * fp * 33.) ** 2)
    w4 = 1. / (1. + (2.6 * fp * 128.) ** 2)
    w5 = 1. / (1. + (2.6 * fp * 430.) ** 2)
    dzx = (dzx + .0055 * w2 * d2x * 8.5 + .0016 * w3 * d3x * 33.
           + .00040 * w4 * d4x * 128. + .00009 * w5 * d5x * 430.)
    dzy = (dzy + .0055 * w2 * d2y * 8.5 + .0016 * w3 * d3y * 33.
           + .00040 * w4 * d4y * 128. + .00009 * w5 * d5y * 430.)

    # --- the bullnose, as a normal in (s, z)
    d = np.clip(SBUL - s, 0., BULR)
    nz0 = np.sqrt(np.maximum(BULR * BULR - d * d, 0.)) / BULR
    ns0 = np.where(s < SBUL, -d / BULR, 0.)
    Nx, Ny, Nz = ns0 * gx - dzx * nz0, ns0 * gy - dzy * nz0, nz0
    inv = 1. / np.sqrt(Nx * Nx + Ny * Ny + Nz * Nz)
    Nx, Ny, Nz = Nx * inv, Ny * inv, Nz * inv

    # --- splash. The stone within ~15 cm of the lip is never dry at 18:41.
    wr = WET * (.55 + .90 * vnoise(x * 2.6 + 31., y * 2.6 + 17.))
    wet = np.clip(1. - (s - SLIP) / np.maximum(wr, .02), 0, 1) ** 1.4
    spot = (np.clip((vnoise(x * 5.5 + 3., y * 5.5 + 9.) - .60) / .18, 0, 1) *
            np.clip(1. - (s - SLIP) / .60, 0, 1))
    wet = wet * (.62 + .76 * vnoise(x * 9.5 + 51., y * 9.5 + 13.))   # splash is patchy
    wet = np.where(cop, np.maximum(wet, .60 * spot), .35 * spot)
    wet = np.minimum(wet * 1.35, 1.)

    # --- albedo
    ks = np.where(cop, np.floor((along + .19 * side) / .55), np.floor((x + .46 * (row % 2.)) / .92))
    kt = np.where(cop, side, row)
    t1, t2 = _hash(ks, kt, 3.1), _hash(ks, kt, 11.7)
    # ? Warm sandstone, pink-tan -- a visual reading of bar section B2's close
    # ? frame of the coping, not a measurement. The previous values were a
    # ? neutral grey-beige and rendered at saturation 0.20; the green is pulled
    # ? down 5% against the red, which is what separates a sandstone from a
    # ? limestone. The illuminant was already corrected (SKY_DECK), so this is
    # ? the albedo half of the same finding and nothing else moved.
    alb = np.where(cop[:, None], np.array([.715, .572, .438])[None],
                   np.array([.676, .536, .414])[None])
    alb = alb * (1. + .46 * (t1 - .5))[:, None]
    alb = alb * (1. + np.stack([.20 * (t2 - .5), .03 * (t2 - .5), -.21 * (t2 - .5)], 1))
    alb = alb * (1. + .13 * (n1 - .5) + .11 * w2 * (n2 - .5) + .09 * w3 * (n3 - .5)
                 + .07 * w4 * (n4 - .5) + .05 * w5 * (n5 - .5))[:, None]
    alb = alb * (1. - .42 * jm)[:, None]
    alb = alb * (1. - .22 * jw * vnoise(x * 3.3 + 61., y * 3.3 + 41.))[:, None]
    alb = alb * (1. - .54 * wet)[:, None]

    # --- light
    L = SUN_DIR
    ndl = np.clip(Nx * L[0] + Ny * L[1] + Nz * L[2], 0, 1)
    vis = np.asarray(sun_vis(x, y), float)
    lift = SAIL_TAU * (1. - vis) * sail_glow(x, y)
    skyv = (.55 + .45 * Nz) * (1. - .40 * jm)
    pf = np.clip(-(Nx * gx + Ny * gy), 0, 1)          # how much it faces the pool
    # The water's own light on the stone, in two parts that used to be one:
    #   level  -- WBOUNCE, the DC. Without it the bullnose renders black.
    #   shape  -- deck_water, the LENSED pattern and the derived falloff. The
    #             pattern is the ratio of the traced water-out gather to the same
    #             gather over a FLAT surface, so its mean is one by construction
    #             and it modulates the DC instead of adding energy to it.
    # 0.10 is still a `?`: it is the share of a nominally horizontal stone facet
    # that sub-pixel relief tips far enough poolward to see the water at all.
    pat, fal = deck_water(along, side.astype(np.int64), s)
    wv = (.95 * pf + .10 * Nz) * fal * (1. - .40 * jm)
    col = alb * (SUN_COL[None] * (ndl * vis + SUN_DIR[2] * lift)[:, None] * .30
                 + SKY_DECK[None] * skyv[:, None]
                 + WBOUNCE[None] * pat * wv[:, None])

    Vx, Vy, Vz = -vdir[:, 0], -vdir[:, 1], -vdir[:, 2]
    Hx, Hy, Hz = L[0] + Vx, L[1] + Vy, L[2] + Vz
    hn = 1. / np.sqrt(Hx * Hx + Hy * Hy + Hz * Hz)
    Hx, Hy, Hz = Hx * hn, Hy * hn, Hz * hn
    ndh = np.clip(Nx * Hx + Ny * Hy + Nz * Hz, 0, 1)
    vdh = np.clip(Vx * Hx + Vy * Hy + Vz * Hz, 0, 1)
    ndv = np.clip(Nx * Vx + Ny * Vy + Nz * Vz, 1e-3, 1)
    m = 12. + 300. * wet
    Fs = .045 + .955 * (1. - vdh) ** 5
    col = col + (SUN_COL[None] * (Fs * (m + 8.) / (8. * np.pi) * ndh ** m
                                  * ndl * vis * .30)[:, None])
    Fv = .045 + .955 * (1. - ndv) ** 5
    return col + SKY_AMB[None] * (Fv * (.09 + .55 * wet))[:, None]


# --------------------------------------------------------- THE FREEBOARD BAND
# Bar section B2b, and the receiver the water-out gather above was built for.
# A poolward-facing VERTICAL strip standing directly on the surface is the best
# receiver in the frame for the water's own thrown light -- better than the
# coping, and for a reason that is geometry rather than taste:
#
#   * the flat-water form factor is SCALE INVARIANT. A vertical facet over an
#     infinite plane collects the same irradiance at 6 mm as at 600 mm, so the
#     band is not brighter than the coping because it catches more light.
#   * what does change with height is the PATCH OF SURFACE it integrates. The
#     gather's weight peaks at rho = qz, so a facet 6 mm up reads a centimetre
#     of water while one 120 mm up reads a decimetre. That is the mechanism B2b
#     is pointing at -- and MEASURED IT IS WEAK over this band: the pattern
#     contrast runs 0.17 at 6 mm to 0.14 at 120 mm, against 0.16 for the stone
#     at the lip. 6 to 120 mm of blur is small against a 20 cm net, so the band
#     does NOT out-contrast the coping per unit area. What it actually wins is
#     ORIENTATION and AREA: it faces the pool with pf = 1 over an unbroken
#     100 mm of vertical face, where the stone gets the same gather through the
#     0.95*pf + 0.10*Nz of a bullnose and a few joint flanks. Both numbers are
#     printed, so the claim is checkable rather than asserted.
#   * and it is the LINER, not a material of its own: the same pigment as the
#     bed with no water over it. Whether that reads PALE, as the sixth
#     photograph shows it, is then a lighting question and not a pigment one --
#     the only band this frame can see is on the north wall, whose poolward
#     normal has N.L < 0 against a due-west sun, so it is a shaded receiver and
#     comes out DARKER than the sunlit water rather than paler. The east wall's
#     band has N.L = 0.93 and would read pale. That is measured and printed
#     after the render rather than corrected by a second colour.
#
# THE OWNER'S READING OF THIS BAND, and the calibration it buys:
#   "That edge is the colour of the walls and floor of the pool. The cyan is
#    what the water and the light add."
# The pigment half is exactly right and the mechanism runs the other way, which
# is this project's own doctrine: with b_b ~ 0 the column has no body colour and
# can only SUBTRACT. It takes red -- ABS is 0.262/m over the red band against
# 0.0102 over the blue -- and what survives READS as cyan. So the dry band and
# the bed are one material differing by one path, and the frame therefore
# carries its own absorption regression; it is printed at the end of the run.
def liner_band(x, y, z, vdir):
    """The freeboard: FREEB of the pool's own blue liner with BEAD of grey
    concrete over it, both vertical and facing the pool, both DRY. Returns the
    radiance and the irradiance that produced it, because the second is what
    makes the band's colour a measurement of the liner rather than of the
    lighting."""
    along, side, gx, gy, _e = _run(x, y)
    sd = side.astype(np.int64)
    Nx, Ny = -gx, -gy                       # poolward horizontal, so Nz = 0
    h = z - waterline(along, sd)            # height over the LOCAL water level
    bead = z > FREEB                        # the grey concrete over the blue

    # --- albedo. ONE material for the blue, and it is the one already here:
    # the same 0.74 * LINER_TINT that `liner()` puts on the bed and that
    # WBOUNCE is built from. No second colour is introduced, on purpose.
    alb = np.broadcast_to(0.74 * LINER_TINT[None], (len(x), 3)).copy()
    # the calcium bloom of `tiles`, continued across the waterline instead of
    # being cut off at it -- it deposits at the MEAN level, so it is a function
    # of z and does not wobble with h.
    cal = np.exp(-((z + .0095) / .0115) ** 2)
    w = (.78 * cal)[:, None]
    alb = alb * (1 - w) + np.array([.95, .91, .84])[None] * w
    # the wet foot: everything the surface has recently covered, which is the
    # meniscus climb plus the wobble the waterline itself carries. Both are
    # derived (MENIS_H, ETA_RMS), and the darkening is the wet-albedo above.
    wetb = np.clip(1. - h / WETTOP, 0, 1) ** .8
    alb = alb * (1 - wetb[:, None]) + wet_albedo(alb) * wetb[:, None]
    # ? the bead's albedo is a visual reading of the sixth photograph, in the
    # ? same status as the sandstone's: neutral grey concrete, slightly cool.
    alb = np.where(bead[:, None], np.array([.40, .41, .42])[None], alb)

    # --- light. A vertical facet's cosine-weighted hemisphere splits EXACTLY in
    # half at the horizon -- sky above, water below -- so each half gets 0.50 and
    # neither number is a choice. The lip cannot shade this face (the bullnose
    # rolls away from the pool above it), so the sun term takes the sail's
    # shadow alone and not coping_vis.
    L = SUN_DIR
    ndl = np.clip(Nx * L[0] + Ny * L[1], 0, 1)
    vis = np.asarray(sail_vis(x, y), float)
    lift = SAIL_TAU * (1. - vis) * sail_glow(x, y)
    pat, fal = band_water(along, sd, z)
    E = (SUN_COL[None] * (ndl * vis + SUN_DIR[2] * lift)[:, None] * .30
         + SKY_DECK[None] * .50
         + WBOUNCE[None] * pat * (.50 * fal)[:, None])
    col = alb * E

    # --- and the grazing sheen. A poolward-facing vertical face reflects the
    # water in front of it, NOT the sky: the mirror direction from a horizontal
    # normal to an eye above it points down into the basin. So the source is
    # WBOUNCE. `?` R_EXT is water's; a dry PVC sheet is nearer 0.043 at normal
    # incidence, and identical to this at the grazing angle the band is seen at.
    Vx, Vy = -vdir[:, 0], -vdir[:, 1]
    ndv = np.clip(Nx * Vx + Ny * Vy, 1e-3, 1)
    # ? the 0.25 on the bead: cast concrete is rough where a vinyl sheet is not,
    # ? so most of its Fresnel goes into a lobe far wider than this view.
    Fv = R_EXT[None] + (1. - R_EXT[None]) * (1. - ndv)[:, None] ** 5
    return col + WBOUNCE[None] * Fv * np.where(bead[:, None], .25, 1.), E


def paving(x, y, z, s, vdir, fp):
    """Everything a downgoing ray that missed the water can hit. The height
    field drops vertically from the coping's lip to the still surface, so a hit
    BELOW that lip is on the freeboard band and a hit at or above it is stone --
    one test, and it is exact because the deck is flat at ZD and the bullnose
    bottoms out at ZLIP."""
    out = _stone(x, y, s, vdir, fp)
    b = z < ZLIP - 1e-5
    if b.any():
        out[b] = liner_band(x[b], y[b], z[b], vdir[b])[0]
    return out


# --------------------------------------------------------------------------- camera
fwd = TGT - EYE; fwd /= np.linalg.norm(fwd)
rgt = np.cross(fwd, [0, 0, 1.]); rgt /= np.linalg.norm(rgt)
upv = np.cross(rgt, fwd)
PX, PY = np.meshgrid((np.arange(W) + .5) / W * 2 - 1, 1 - (np.arange(H) + .5) / H * 2)
tf = np.tan(FOV / 2)
D = (fwd[None, None] + rgt[None, None] * (PX * tf * W / H)[..., None]
     + upv[None, None] * (PY * tf)[..., None])
D /= np.linalg.norm(D, axis=2, keepdims=True)
D = D.reshape(-1, 3)


# The box filter that turns SS x SS subsamples into one pixel is already an
# integral; make it do the SPECTRAL integral at the same time and it costs
# nothing. Each subsample of a pixel is given a different wavelength stratum
# inside its channel's band, laid out as a Latin square over the SS x SS grid so
# that the spectral index is decorrelated from the sub-pixel position in both
# axes -- otherwise the band integral would come out as a sub-pixel colour ramp
# instead of a mean. (4i + 3j) mod 9 is a bijection on the 3x3 grid and moves by
# 4 and 3 strata between neighbours, which is the most spread available.
NSPEC = SS * SS
_LATIN = np.array([[(4 * i + 3 * j) % NSPEC for j in range(SS)] for i in range(SS)])
SUBK = np.tile(_LATIN, (H // SS, W // SS)).ravel().astype(np.int8)


def project(P):
    """World point -> pixel in the ENCODED image (after the SS box filter), so
    the crops below are aimed at geometry rather than at remembered numbers."""
    d = np.atleast_2d(np.asarray(P, float)) - EYE[None]
    f = np.maximum(d @ fwd, 1e-6)
    return np.stack([(((d @ rgt) / f / (tf * W / H) + 1) * .5 * W - .5) / SS,
                     ((1 - (d @ upv) / f / tf) * .5 * H - .5) / SS], -1)


def tri(o, d, a, b, c):
    e1, e2 = b - a, c - a
    p = np.cross(d, e2); det = p @ e1
    inv = 1. / np.where(np.abs(det) < 1e-12, 1e-12, det)
    t = o - a; u = (t @ p.T) * inv
    q = np.cross(t, e1); v = (d @ q) * inv; s = (e2 @ q) * inv
    return (u >= 0) & (v >= 0) & (u + v <= 1) & (s > 1e-4)


hit_sail = np.zeros(W * H, bool)
for t3 in ((0, 1, 2), (0, 2, 3)):
    hit_sail |= tri(EYE, D, SAIL[t3[0]], SAIL[t3[1]], SAIL[t3[2]])

# --- trace the pool edge as a height field ---------------------------------
# gh() is flat almost everywhere, so almost every ray is settled by an endpoint
# test and only the band of pixels that actually straddles the coping is marched.
# Written as a FUNCTION of the ray set rather than over the fixed pixel grid,
# because the adaptive edge pass below has to be able to fire extra rays through
# a pixel and get exactly the same answer the primary grid would have given.
Ex, Ey, Ez = EYE


def trace_edge(dvec):
    """(t, s, is_water) where a set of camera rays meets the pool edge field."""
    dz = dvec[:, 2]
    with np.errstate(divide='ignore', invalid='ignore'):
        tt = (ZD - Ez) / dz               # plane of the coping top
        tw = (0.0 - Ez) / dz              # the still waterline
    dn = dz < -1e-9
    tt = np.where(dn, tt, BIG)
    tw = np.where(dn, tw, BIG)
    sa = pool_s(Ex + dvec[:, 0] * tt, Ey + dvec[:, 1] * tt)
    sb = pool_s(Ex + dvec[:, 0] * tw, Ey + dvec[:, 1] * tw)
    # THE SHORTCUT NEEDS CONVEXITY, and says so. pool_sdf is convex for the box,
    # so on the 75 mm segment between the coping-top plane and the waterline it
    # never exceeds its endpoints: both ends inside the lip proves the whole ray
    # is over open water, and no march is needed. A freeform boundary with a
    # concave lobe -- a kidney's waist, a step unit cut out of the water --
    # breaks that, and the endpoints would silently certify a ray that clips
    # stone in between. So the shortcut is GATED on POOL_CONVEX rather than
    # assumed; with it off every downgoing ray is marched, about 30x the cost on
    # this band of pixels. 8 mm of slack covers the laid-stone wobble, which is
    # not convex either.
    if POOL_CONVEX:
        iw = dn & (np.maximum(sa, sb) < SLIP - .008)
        ip = dn & (sa >= SBUL + .008)
    else:
        iw = dn & (np.maximum(sa, sb) < SLIP - .30)
        ip = dn & (np.minimum(sa, sb) >= SBUL + .30)
    mar = np.flatnonzero(dn & ~iw & ~ip)
    th = np.where(iw, tw, np.where(ip, tt, BIG))
    if mar.size:
        t0, t1 = tt[mar], tw[mar]
        dx, dy, dz2 = dvec[mar, 0], dvec[mar, 1], dvec[mar, 2]
        lo, hi, prev = t0.copy(), t1.copy(), t0.copy()
        got = np.zeros(mar.size, bool)
        for k in range(1, 25):
            t = t0 + (t1 - t0) * (k / 24.)
            f = (Ez + dz2 * t) - gh(Ex + dx * t, Ey + dy * t)
            n = (~got) & (f <= 0)
            lo = np.where(n, prev, lo); hi = np.where(n, t, hi)
            got |= n; prev = t
        lo = np.where(got, lo, t1); hi = np.where(got, hi, t1)
        for _ in range(16):
            m = .5 * (lo + hi)
            f = (Ez + dz2 * m) - gh(Ex + dx * m, Ey + dy * m)
            lo = np.where(f > 0, m, lo); hi = np.where(f > 0, hi, m)
        th[mar] = hi
    sh = pool_se(Ex + dvec[:, 0] * th, Ey + dvec[:, 1] * th)
    # WATER OR WALL, DECIDED ON THE HEIGHT OF THE HIT AND NOT ON ITS s. The two
    # tests look interchangeable and are not, and the difference is most of the
    # band. The freeboard is a VERTICAL face standing at s = SLIP, so every ray
    # that lands on it converges to s = SLIP to the bisection's own tolerance --
    # (t1 - t0)/24/2^16, about 3e-7 m of lateral travel -- and asking whether s
    # is below SLIP by 1e-7 is then a coin toss on the last bits of the march.
    # MEASURED: 80% of the band's rays were being handed to water_shade, which
    # shaded them as a water surface climbing the wall. It never showed, because
    # the ambient meniscus lift that used to sit in water_shade landed that
    # surface within one sRGB level of the band beside it; removing the lift and
    # putting the derived specular line in its place is what exposed it, as a
    # 40-pixel dither over the whole band. The height test has the band's own
    # ZLIP of margin instead of 1e-7: a water hit converges to z <= 0 by
    # construction (the march keeps f = z - gh <= 0 and gh = 0 over water),
    # while every hit on the band face is at 0 < z < ZLIP.
    zh = Ez + dvec[:, 2] * th
    return th, sh, dn & (zh < 1e-6), mar.size, dn.sum()


t_hit, S_HIT, _isw, _nmar, _ndn = trace_edge(D)
print("edge march: %d of %d rays (%.2f%%) straddle the coping"
      % (_nmar, _ndn, 100. * _nmar / max(_ndn, 1)))
hx, hy = Ex + D[:, 0] * t_hit, Ey + D[:, 1] * t_hit
inp = _isw & ~hit_sail
pav = (D[:, 2] < -1e-9) & ~hit_sail & ~inp
bgm = ~hit_sail & ~inp & ~pav             # nothing: the frame is water and stone

PIXANG = 2. * np.tan(FOV / 2.) / H
FOOT = t_hit * PIXANG / np.maximum(np.abs(D[:, 2]), .10)
# THE FOOTPRINT THE FILTER IS FED, and the one line where a caller can get the
# whole thing wrong. FOOT is one SUBSAMPLE of the SS x SS grid; the pixel the
# image is stored at is SS times larger, and the difference decides the answer
# rather than trimming it. Two independent reasons the output pixel is the right
# one, and they point the same way:
#   * SAMPLING. At 8 m the two are 8.6 and 25.8 mm while the wind band's
#     dominant wave is 28 mm -- comfortably resolved by the subsample grid,
#     hopelessly aliased by the grid the picture is kept on. Prefilter at the
#     subsample rate and the moire survives into the file.
#   * NONLINEARITY, which is the conservative half. Shading is not linear in
#     slope -- Fresnel is a fifth power and the specular lobe is an exponential
#     -- so a slope field sitting merely AT the subsample Nyquist still makes
#     radiance harmonics well above it. Band-limiting the slope to the sampling
#     rate does not band-limit what the shader makes of it, so the prefilter
#     belongs at the rate the final image is stored at.
FOOT_PX = FOOT * SS

# --- what the water does within a hand's width of the wall -------------------
# Three separate things, all of them missing before, and together they are the
# whole reason a pool edge does not read as a cut in a coloured rectangle.
#  1  the reflection.  The coping stands 75 mm over the water and overhangs the
#     wall by 20 mm, so a reflected ray heading at the wall from close in hits
#     the underside of the stone instead of the sky.  That is the dark band that
#     hugs every real pool edge, and it wobbles because the ripples aim the ray.
#  2  the ambient.  Under the overhang the water sees a fraction of the sky.
#  3  the meniscus.  Water wets the wall and climbs it; the curved sliver is
#     brighter than the flat surface next to it.
COP_REFL = np.array([.62, .57, .48]) * (SKY_DECK * .40 + WBOUNCE * .85)
# ...and what the water reflects there is now mostly LINER rather than stone. Of
# the ZD of vertical face a near-wall reflected ray can strike, FREEB is blue
# liner, BEAD is grey concrete and only the top BULR is the bullnose's underside.
# Leaving COP_REFL alone would have the water reflecting a sandstone colour off a
# surface this round just made blue -- an inconsistency introduced by the change
# itself, so it is closed here. `?` in the WEIGHTING only: `over` below already
# knows the height on the face the ray strikes, but resolving the mix per ray
# needs the band's along-wall lookup inside water_shade, which is a pass of its
# own. The area weighting is the mean of that, and it is exact for the mean.
BAND_REFL = 0.74 * LINER_TINT * (SKY_DECK * .50 + WBOUNCE * .50)
BEAD_REFL = np.array([.40, .41, .42]) * (SKY_DECK * .50 + WBOUNCE * .50)
EDGE_REFL = (FREEB * BAND_REFL + BEAD * BEAD_REFL + BULR * COP_REFL) / ZD
print("what the water reflects at the wall: %s, of which %.0f%% is liner band, "
      "%.0f%% bead, %.0f%% stone (was the stone's own %s)"
      % (np.round(EDGE_REFL, 3), 100 * FREEB / ZD, 100 * BEAD / ZD,
         100 * BULR / ZD, np.round(COP_REFL, 3)))
# --------------------------------------------- THE MENISCUS, AS A FLUX INTEGRAL
# The meniscus, with its width DERIVED instead of guessed. Water wets the wall
# and climbs it; the 2-D static meniscus on a vertical wall is exactly
#     z = 2 a sin(phi/2),      a = sqrt(sigma / rho g) = 2.72 mm
# with phi the surface's inclination to the horizontal, so the climb at the wall
# is h = a sqrt(2(1 - sin theta_c)) -- 3.85 mm at perfect wetting, 2.72 mm at a
# 30 deg contact angle -- and the fillet decays over a couple of capillary
# lengths. The 10 mm e-folding that used to be here was about twice that and was
# not derived from anything.
#
# WHAT USED TO SIT HERE WAS AN AMBIENT LIFT AND THE MECHANISM IS SPECULAR. Two
# builders wrote that down and deferred it; this is the pass that builds it.
# Across the strip the tilt runs continuously from 0 at the flat surface to
# phi_w = 90 - theta_c at the wall, so the strip holds EVERY facet orientation in
# one plane and the mirror condition is met inside it for anything bright in the
# sky -- the one specular feature in this scene that cannot fail the
# reachability test the spec-C diagnostic applies to the open surface.
#
# THE INTEGRAL, AND WHAT IT IS DIVIDED BY. Differentiating the profile gives
# dz = a cos(phi/2) dphi and dz/dx = -tan(phi), so the surface at tilt phi
# occupies
#       dx = a cos(phi/2) cos(phi) / sin(phi) dphi     (horizontally)
#       ds = a cos(phi/2)          / sin(phi) dphi     (of arc)
# and both are needed: the first says WHERE the facet is (which decides whether
# the coping's undercut is in front of its mirror direction) and the second says
# how much surface there is. A camera ray does not see the fillet, it sees a
# pixel; so what is computed is a RADIANT INTENSITY PER UNIT LENGTH OF WATERLINE
#
#   I(v) = int_0^phi_w [ F(n.v) L_env(R(phi)) (n.v) / cos(phi)
#                        - F(v_z) L_env(R_flat) v_z ] dx                 (W/sr/m)
#
# -- the fillet MINUS the flat surface it replaces, because water_shade has
# already shaded that flat surface over the same millimetres and the term added
# here has to be the excess or the baseline is counted twice. The subtraction is
# also what makes the integral converge: dx diverges logarithmically as phi -> 0
# while the bracket vanishes linearly in phi, so the product is finite and the
# far tail costs nothing.
#
# The division is by the PIXEL FOOTPRINT MEASURED ACROSS THE WATERLINE. Writing
# the result back as an equivalent radiance on the still plane,
#       L_add(d) = I(v) P(d) / |v_z|,     int P dd = 1
# any pixel that integrates L_add over its own footprint then gets exactly
# I(v) * (length of waterline it contains) / (its solid angle * r^2), which is
# the correct answer at every scale and needs no clamp: P is the fillet's own
# d-profile convolved with the footprint, so where the fillet is resolved (the
# footprint runs 3.7 mm at the near end of the north wall) it is a profile, and
# where it is not (9.9 mm at the far end, against a 2.3 mm bright strip) the
# same expression is a flux spread over one pixel. The chapter's "below ~1 px
# clamp the screen width and scale the intensity by the same ratio" is what
# that degenerates to; doing it as a convolution gets both regimes from one
# expression and cannot produce the dashed line the clamp is warning about.
#
# THE FOLD AT d = 0. The convolution puts part of the flux at d < 0, which is
# the WALL side of the junction -- and that is where it belongs: the fillet's
# upper end stands h = 3.85 mm UP the wall, which this frame projects to 0.4-1.1
# output pixels above the junction, i.e. onto the band's wet foot. Depositing it
# there would move BAND_COL and the absorption regression that is measured off
# it, so it is reflected back into the water side instead: flux-conserving, and
# wrong by less than the pixel it is already spread over. `?` in the placement
# only, never in the amount.
#
# WHICH WALL GETS THE SUN AND WHICH GETS THE HORIZON, derived rather than
# assumed. A meniscus tilts only perpendicular to its own waterline, so with
# t the along-wall unit vector and m the poolward one the reachable normals are
# n(phi) = sin(phi) m + cos(phi) z, a one-parameter family in the (m, z) plane.
# Reflecting v about it leaves the out-of-plane component alone -- R.t = -v.t for
# every phi -- and rotates the in-plane part at twice the rate, so with
# theta_v = atan2(v.m, v.z) and theta_l = atan2(L.m, L.z),
#       R(phi) . L = sin(A) sin(B) + cos(A) cos(B) cos(2(phi - phi*))
#       A = asin(-v.t),  B = asin(L.t),  phi* = (theta_v + theta_l) / 2
# EXACTLY. Two consequences, and neither is the azimuth rule of thumb:
#   * the closest the mirror direction ever comes to the sun is beta = A - B,
#     which is zero where (L + v).t = 0. That is the half-vector test, and
#     because v sweeps along the wall it is satisfied at ONE POINT on each of
#     the four walls, not on two of them -- the eye is 3-9 m away, not at
#     infinity, so "the sun is due west" does not by itself rule a wall out.
#   * what rules a wall out is the COPING. The sun's mirror direction leaves at
#     the in-plane angle theta_l, and the fillet sits millimetres from a wall
#     carrying a lip ZD above it, so a mirror direction with any wallward tilt
#     at all is looking at the underside of the stone. theta_l < 0 exactly when
#     L.m < 0, so the sun's line is reachable on a wall if and only if the sun
#     is on the POOLWARD side of that wall's vertical plane -- which is the same
#     statement as the coping-shadow print at the top of this file (312 mm of
#     water shaded off the west wall, 20 mm off the north), arrived at from the
#     reflected side instead of the incident one.
# For this scene that is: sun reachable on the EAST and SOUTH walls, occluded on
# the NORTH and WEST. Both are built -- the disc is integrated analytically
# because the 0.53 deg it subtends selects ~15 um of fillet that no quadrature
# would sample, and the rest of the sky is integrated numerically -- and which
# one lands where is measured and printed below rather than hard-coded.
#
# WHAT IS NOT BUILT, so that it is not read as built: the fillet also REFRACTS,
# and a facet at 45 deg sends the camera ray somewhere quite different inside the
# water. The transmitted column is 10x the reflected one, so that term is
# potentially larger than this one; it needs the traced geometry rather than an
# environment lookup and it is a pass of its own. This one is the specular half,
# which is the half the chapter says carries the line.
# CAP_A / MENIS_H / MENIS_W / THETA_C / PHI_W are defined with the pool-edge
# section above, because the liner band's wet foot needs them too.
MENIS_N = 64


def menis_tables(theta_c, a, n=64):
    """The fillet's quadrature at a given contact angle and capillary length:
    (phi, dx, d, z, sin, cos, reach), midpoint rule over phi in [0, 90 - theta_c].

    A function rather than seven inline lines because THE TWO LIMITS THAT GUARD
    THIS FILE ARE TAKEN BY CALLING IT. As a -> 0 the fillet has no size and every
    term must go to zero; as theta_c -> 90 deg the climb collapses and it must go
    to zero again, leaving exactly the flat-surface answer. Neither limit can be
    reached by a test that rebuilds the table itself, because then the test and
    the code are the same table twice. `validate.py` installs the result of this
    function over the module's own and re-runs the shipped `meniscus`."""
    phw = np.pi / 2 - theta_c
    ph = (np.arange(n) + .5) / n * phw                  # tilt nodes, midpoint
    dx = a * np.cos(ph / 2) * np.cos(ph) / np.sin(ph)   # dd/dphi
    wd = dx * (phw / n)                                 # the node's width in d
    d = np.cumsum(wd[::-1])[::-1] - .5 * wd             # d(phi), from the wall
    return ph, wd, d, 2. * a * np.sin(ph / 2), np.sin(ph), np.cos(ph), float(wd.sum())


(_mph, MENIS_WD, MENIS_D, MENIS_Z, MENIS_SIN, MENIS_COS,
 MENIS_REACH) = menis_tables(THETA_C, CAP_A, MENIS_N)
# THE FORCE BALANCE THE TABLE HAS TO SATISFY, printed because it is the one
# statement about this quadrature that does not come from the profile at all.
# The weight of the liquid the fillet raises above the far-field level, per unit
# of waterline, is carried by the vertical pull of the surface at the wall:
#       rho g INT z dx  =  sigma cos(theta_c)  =  sigma sin(phi_w)
# and with z = 2a sin(phi/2), dx = a cos(phi/2) cos(phi)/sin(phi) dphi the left
# side integrates to rho g a^2 sin(phi_w) = sigma sin(phi_w), identically. It is
# a global balance on the SAME two tabulated columns the flux integral sweeps,
# arrived at from Newton rather than from Young-Laplace, so a table that is
# self-consistently wrong fails it. `validate.py` asserts it; the residual is
# quadrature error and nothing else.
MENIS_LIFT = float((MENIS_Z * MENIS_WD).sum() * 1000.0 * 9.81)
print("the fillet's force balance: rho g INT z dx = %.5f N/m against sigma "
      "cos(theta_c) = %.5f N/m, %.2f%% apart on %d nodes -- the quadrature's own "
      "error, and the only check on the profile that is not the profile"
      % (MENIS_LIFT, SIGMA_W * np.sin(PHI_W),
         100 * abs(MENIS_LIFT / max(SIGMA_W * np.sin(PHI_W), 1e-30) - 1), MENIS_N))
print("the fillet as a quadrature: %d tilt nodes over 0-%.0f deg; the surface at "
      "tilt phi stands %s mm from the wall at phi = 80/60/45/30/20/10 deg, so "
      "the whole of it above 30 deg is inside %.2f mm and the tabulated reach is "
      "%.1f mm"
      % (MENIS_N, np.degrees(PHI_W),
         " / ".join("%.2f" % (1000 * np.interp(np.deg2rad(t), _mph, MENIS_D))
                    for t in (80, 60, 45, 30, 20, 10)),
         1000 * np.interp(np.deg2rad(30), _mph, MENIS_D), 1000 * MENIS_REACH))


def _erf(x):
    """Abramowitz & Stegun 7.1.26, |err| < 1.5e-7. Needed to CLIP the analytic
    lobe integral to the tilts the fillet actually has: phi* can sit outside
    [0, phi_w] and the Gaussian must be truncated there, not extrapolated."""
    s, a = np.sign(x), np.abs(x)
    t = 1. / (1. + .3275911 * a)
    y = 1. - ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t
               - .284496736) * t + .254829592) * t * np.exp(-a * a)
    return s * y


def _env_menis(rx, ry, rz):
    """The environment along a fillet's mirror direction. The same sky() the open
    water reads, MINUS the disc -- which is integrated analytically below and
    would otherwise be counted twice, and which a 64-node sweep would hit or miss
    at random anyway. Sub-horizon directions are not clamped to the horizon
    colour: a mirror direction below the horizon is looking at the water further
    out, so it gets one bounce off it -- Fresnel of the sky it would mirror, plus
    what is coming UP out of the pool through the rest."""
    az = np.abs(rz)
    t = az[:, None] ** .55
    col = SKY_HOR[None] * (1 - t) + SKY_TOP[None] * t
    cs = np.clip(rx * SUN_DIR[0] + ry * SUN_DIR[1] + az * SUN_DIR[2], 0, 1)
    for amp, n, c in SKY_LOBE[1:]:                    # every lobe but the disc
        col = col + c[None] * amp * (cs ** n)[:, None]
    col = col * 1.15
    fw = fresnel(az)                                  # exact, not Schlick
    return np.where((rz >= 0)[:, None], col, fw * col + (1 - fw) * WBOUNCE[None])


def _menis_weights(Vm, Vz):
    """The fillet's PROJECTED AREA toward the eye, node by node, and that of the
    flat strip it replaces -- per unit length of waterline, in metres.

    Fresnel-free and environment-free: this is the geometry both columns share,
    and it is factored out so that it can be measured a completely different way.
    `V` points from the surface TOWARD the eye, decomposed on the wall's own
    (poolward, along, up) frame; only Vm and Vz enter, because the fillet's
    normal has no along-wall component.

        n(phi).V = sin(phi) Vm + cos(phi) Vz
        w_fil = ds (n.V) = dx (n.V)/cos(phi)      the facet's projected area
        w_flt = dx  Vz                            the flat strip's

    BOTH ARE GATED ON THE SAME VISIBILITY, and that is the whole of the second
    line. A facet with n.V <= 0 turns away from the eye, and on a NEAR wall --
    where the eye looks poolward over the coping -- that is every facet steeper
    than atan(Vz/|Vm|), because the fillet's own crest at the wall stands in
    front of them. Over that stretch of d the flat model drew flat water and the
    real scene shows the crest and the wall above it. Subtracting the flat strip
    there while adding nothing back is not conservative and not small: it is the
    whole TRANSMITTED column over a centimetre of width, and it read as -2.1e-3
    W/sr/m on the east wall against +1.6e-3 on the west. The gate was latent
    while only the reflected half existed (Fresnel 0.05 made the hole invisible)
    and the transmitted half is what exposed it.

    WHAT THE GATED SUM IS, exactly. With ds sin(phi) = dz and ds cos(phi) = -dd,

        SUM (w_fil - w_flt) = INT (Vm dz - Vz dd) - Vz INT (-dd)
                            = Vm z(phi*)

    where phi* is the steepest visible tilt -- phi_w, and so z = h, whenever the
    eye is poolward of the fillet. The excess projected area of the fillet is the
    poolward view component times the CLIMB, and nothing else: a projected-area
    identity, true for any monotone profile, which the quadrature nowhere
    encodes and which `validate.py` asserts against this function's own output
    and against a brute-force parallel-ray march of the analytic profile."""
    Vm = np.asarray(Vm)
    Vz = np.asarray(Vz)
    ndv = MENIS_SIN[None] * Vm[:, None] + MENIS_COS[None] * Vz[:, None]
    vis = ndv > 0.
    w_fil = np.where(vis, ndv, 0.) / MENIS_COS[None] * MENIS_WD[None]
    w_flt = np.where(vis, np.maximum(Vz, 0.)[:, None], 0.) * MENIS_WD[None]
    return ndv, w_fil, w_flt


def _riser_shade(hxr, hyr, hzr, ci, c, mode):
    """A cylindrical riser of the step unit. No caustic map is rasterised for
    these faces: the caustic pass drops the rays that reach them (that IS the
    cast shadow), and the mean refracted sun grazes them 2.6 deg on the dark
    side wherever the camera can see them. Four terms, in the order they matter:
      * the BOUNCE off the sunlit bed in front, gathered above -- the largest,
        the one that carries the caustic net, and the one whose absence rendered
        this whole region neutral grey;
      * the TIR return, arriving shallow and so favouring a vertical face;
      * sky through the Snell window, over the upgoing half hemisphere only;
      * direct sun, which is nonzero only on the crescent that turns west and is
        never visible from an anti-solar camera. It is kept because it is real,
        not because it is seen."""
    cx = np.array([c_[0] for c_ in CYL])[ci]
    cy = np.array([c_[1] for c_ in CYL])[ci]
    RR = np.array([c_[2] for c_ in CYL])[ci]
    zt = np.array([c_[3] for c_ in CYL])[ci]
    ox, oy = (hxr - cx) / RR, (hyr - cy) / RR
    # eased nosing: the top NOSE_R of the riser rolls over to meet the tread.
    # ? shading-only round-over -- 25 mm is under one pixel of silhouette here.
    th = np.clip((hzr - (zt - NOSE_R)) / NOSE_R, 0, 1) * (np.pi / 4)
    Nx, Ny, Nz = ox * np.cos(th), oy * np.cos(th), np.sin(th)
    d = -hzr
    lev = np.clip(0.74 + 0.030 * (0.5 + 0.5 * np.sin(hxr * 3.1 + .7)
                                  * np.sin(hyr * 4.3 - .4) - 0.6), .05, .95)
    ndl = np.clip(Nx * -TSUN_DIR[0] + Ny * -TSUN_DIR[1] + Nz * -TSUN_DIR[2], 0, 1)
    # ? the caustic that lands on a riser is read off the bed map 30 mm radially
    # ? outside it -- the map is indexed by bed position and a vertical face has
    # ? none. Only the bench crescent is lit at all, so this is a 6-pixel term.
    cau = sample((bed[c] if mode == 'disp' else bed[3])[..., None],
                 hxr + ox * .030, hyr + oy * .030, X0, X1, Y0, Y1)[:, 0]
    aow = bed_ao(hxr, hyr, hzr)
    ao = aow * .5 * (1. + Nz)          # a vertical face sees half the sky
    bnc = riser_bounce(hxr, hyr, hzr, ci)[:, c]
    tir = sample(bedret[..., c:c + 1], hxr, hyr, X0, X1, Y0, Y1)[:, 0] * \
        aow * (TIR_VERT + (1. - TIR_VERT) * Nz)
    return LINER_TINT[c] * lev * (
        SUN_COL[c] * cos_i * TSUN * cau * (ndl / cos_t) * np.exp(-ABS[c] * d / cos_t)
        + SKY_AMB[c] * ao * np.exp(-ABS[c] * d * 1.55)
        + tir + bnc)


# --- THE FILLET'S UNDERSIDE IS NOT ON A CAMERA PATH, and the reason is one line
# A previous round asked whether the strip of surface just poolward of the
# junction, seen from above THROUGH the water, shows the sunlit bed by total
# internal reflection off the fillet's underside -- reflectance exactly 1 past
# 48.5 deg, against 0.02-0.07 for the external specular, which would make it 15
# to 50 times the term that ships. The fillet does hold every tilt, so the
# CRITICAL-ANGLE condition is met inside it by construction; the argument fails
# one step earlier, on whether a camera ray can arrive there at all.
#
# Write the transmitted direction as t = eta i + f n with n opposing i. Then
#       f = eta cos_i - cos_t,   cos_t = sqrt(1 - eta^2 + eta^2 cos_i^2)
#       f > 0  <=>  eta^2 cos_i^2 > 1 - eta^2 + eta^2 cos_i^2  <=>  eta^2 > 1.
# A camera above the water refracts IN, eta = 1/n = 0.749 < 1, so f < 0 strictly
# -- at every incidence, with no exceptions and no grazing limit. A static
# meniscus on a vertical wall carries tilts phi in [0, 90 deg], so its normal has
# n_z = cos(phi) >= 0, and a camera above the water has i_z < 0. Hence
#       t_z = eta i_z + f cos(phi)  <  0     IDENTICALLY,
# and the refracted ray descends everywhere inside the water. It cannot arrive
# at the underside of a surface that lies above it. The fillet's underside
# subtends EXACTLY ZERO solid angle from any camera above the waterline -- not a
# small angle, not one this frame happens to miss; zero, for every eye position,
# every wall and every contact angle.
#
# So the mechanism is real and the geometry never reaches it on a camera path:
# the sweep argument that makes the meniscus SPECULARLY reachable establishes
# that a required tilt exists somewhere in the strip, and reachability of a TILT
# is not reachability of a POSITION. The underside is reached only from below,
# by light already in the water, which is the bed-return term (TIR_FRAC /
# TIR_VERT) and is built. A brute-force march of 215000 refracted camera rays
# against the analytic profile, over all four walls and every tilt, found 0
# underside hits and is the row `validate.py` carries.
MENIS_TIR_REACH = 0.0        # solid angle of the fillet's underside, per camera


def _menis_under(sid, u, v, sm, cyl, tzc, mode):
    """What comes back up a fillet's TRANSMITTED ray: the same bed, wall and
    riser maps `water_shade` reads for the flat surface, with the same
    Beer-Lambert on the leg. Factored out of the loop below for two reasons --
    the flat baseline and the fillet's own column must read it through the same
    code or the subtraction measures the difference between two shaders rather
    than between two geometries, and `validate.py` substitutes a unit radiance
    here to test the fillet's geometry without building the maps."""
    col = np.zeros((sid.size, 3))
    bi, wim = bed_img[mode], wall_img[mode]
    for c in range(3):
        m = sid == 0
        if m.any():
            col[m, c] = sample(bi[..., c:c + 1], u[m], v[m], X0, X1, Y0, Y1)[:, 0]
        for wi, sv in enumerate((1, 2, 3, 4)):
            m = sid == sv
            if m.any():
                a, b = (Y0, Y1) if sv <= 2 else (X0, X1)
                col[m, c] = sample(wim[wi][..., c:c + 1], u[m], v[m],
                                   a, b, -DEPTH, 0.)[:, 0]
        m = sid == 5
        if m.any():
            col[m, c] = _riser_shade(u[m], v[m], tzc[m] * sm[m], cyl[m], c, mode)
    return col * np.exp(-ABS[None] * sm[:, None])


def meniscus(hw_x, hw_y, s_h, dvec, fp, gxx_, gyy_, vxx_, vyy_, vxy_,
             mode='disp', parts=None):
    """The fillet's excess over the flat water it replaces, returned as a
    radiance to add to the ray. Evaluated only on the band of rays whose
    footprint can reach the fillet at all -- everywhere else it is exactly zero,
    which is what makes a 64-node quadrature affordable inside the main path.

    TWO columns, on one quadrature and one set of projected areas:
      * REFLECTED -- the facets mirror sky and sun. Fresnel 0.02-0.07 where this
        camera sees them, which is why it is faint, plus the sun's disc handled
        analytically because 0.53 deg selects ~15 um of fillet that no 64-node
        sweep would find.
      * TRANSMITTED -- the facets are also a cylindrical lens, and a facet turned
        toward the eye passes 0.93-0.98 of what is behind it. The ray is TRACED,
        not looked up: from the node's own position on the profile, refracted
        with the node's own normal, through the same `scene_hit` and the same bed
        / wall / riser maps the flat surface reads. On the walls this frame can
        see it lands on the liner within 20 mm of the waterline; where the fillet
        is on the near wall it goes poolward into the basin instead.
    A third was tested and refuted -- see MENIS_TIR_REACH above; the fillet's
    underside subtends zero solid angle from any camera above the water.

    The subtraction is per column and against the SAME flat surface: `water_shade`
    has already written both a reflected and a transmitted column over these
    millimetres, and what is added here is the excess of each."""
    out = np.zeros((hw_x.size, 3))
    if fp is None:
        return out              # no footprint, no width to spread a flux over
    d = np.maximum(SLIP - s_h, 0.)                # distance in from the waterline
    gx, gy, _e = pool_grad(hw_x, hw_y)
    mx, my = -gx, -gy                             # poolward horizontal, |m| = 1
    tx, ty = -gy, gx                              # along the waterline
    dh = np.maximum(np.hypot(dvec[:, 0], dvec[:, 1]), 1e-9)
    pxh, pyh = dvec[:, 0] / dh, dvec[:, 1] / dh   # view azimuth, and across it
    pm = pxh * mx + pyh * my
    qm = -pyh * mx + pxh * my
    # the footprint ACROSS the waterline. `fp` is the OUTPUT pixel's along the
    # view azimuth (t*eps/|d_z|), so t*eps = fp*|d_z| and the two axes of the
    # footprint ellipse recombine to this. The kernel is the SUBSAMPLE box --
    # the SS x SS box filter supplies the rest of the output pixel's integral,
    # and prefiltering at the output rate here would blur it twice. That is the
    # opposite of the choice FOOT_PX makes upstream, and for the opposite
    # reason: this term is LINEAR in what is deposited, so nothing it makes has
    # harmonics above the rate it is filtered at.
    w_m = np.abs(fp) * np.sqrt(pm * pm + (qm * dvec[:, 2]) ** 2)
    sig = np.maximum(w_m / SS, 2e-4) / np.sqrt(12.)
    sel = np.flatnonzero(d < MENIS_REACH + 3.5 * sig)
    if not sel.size:
        return out
    for c0 in range(0, sel.size, 20000):
        k = sel[c0:c0 + 20000]
        Vm = -(dvec[k, 0] * mx[k] + dvec[k, 1] * my[k])
        Vt = -(dvec[k, 0] * tx[k] + dvec[k, 1] * ty[k])
        Vz = -dvec[k, 2]
        Lt = SUN_DIR[0] * tx[k] + SUN_DIR[1] * ty[k]
        Lm = SUN_DIR[0] * mx[k] + SUN_DIR[1] * my[k]
        # --- the fillet, node by node
        # the projected areas both columns are built on, and the ONLY place the
        # quadrature's geometry is written down -- see `_menis_weights`.
        ndv, W_FIL, W_FLT = _menis_weights(Vm, Vz)
        Rm = 2. * ndv * MENIS_SIN[None] - Vm[:, None]
        Rz = 2. * ndv * MENIS_COS[None] - Vz[:, None]
        Rt = np.broadcast_to(-Vt[:, None], Rm.shape)
        Rx = Rm * mx[k][:, None] + Rt * tx[k][:, None]
        Ry = Rm * my[k][:, None] + Rt * ty[k][:, None]
        # the coping's undercut, tested on the MIRROR direction: a ray heading at
        # the wall from d millimetres away crosses it at over = R_z d / toward,
        # and anything under ZD is stone rather than sky. water_shade's own
        # version of this is a soft ramp in `over`, which is right there -- it
        # stands in for the spread of normals inside one pixel of FLAT water.
        # Here the normal is not a distribution but a quadrature node, so the
        # test is a STEP; leaving it soft lets 11% of a 3.6e5 sun through a
        # coping it is entirely behind. The transition sits at phi = theta_v/2,
        # where the mirror direction runs parallel to the wall, and the 64 nodes
        # resolve it to a node whose width in d is under 0.2 mm.
        tw = -Rm
        ov = np.where(tw > 1e-9, Rz * MENIS_D[None] / np.maximum(tw, 1e-9), BIG)
        occ = np.where((tw > 1e-9) & (ov < ZD), 1., 0.)
        Le = _env_menis(Rx.ravel(), Ry.ravel(), Rz.ravel()).reshape(
            Rm.shape + (3,))
        Le = Le * (1 - occ)[..., None] + EDGE_REFL[None, None] * occ[..., None]
        # Fresnel with the SAME roughness correction water_shade uses, and for
        # the same reason on both sides of the subtraction: the term returned
        # here is an excess over what water_shade already wrote, so if the
        # baseline is priced with the smooth curve and the picture was drawn with
        # Bruneton's, the difference is a 19% error on a quantity of the same
        # size as the answer. `sv` is the one-direction unresolved slope rms
        # along the view azimuth -- `a_` below, the file's own `el[5]`.
        _sv = np.sqrt(np.maximum(pxh[k] ** 2 * vxx_[k]
                                 + 2 * pxh[k] * pyh[k] * vxy_[k]
                                 + pyh[k] ** 2 * vyy_[k], 0.))
        _rgh = (np.exp(-2.69 * _sv) / (1. + 22.7 * _sv ** 1.5))[:, None]
        nc = np.clip(ndv, 1e-4, 1.)
        Ff = F0 + (fresnel(nc) - F0) * _rgh[..., None]
        fil = Ff * Le * W_FIL[..., None]
        # --- the flat surface it replaces, at the same distances
        ov0 = np.where(Vm[:, None] > 1e-9,
                       Vz[:, None] * MENIS_D[None] / np.maximum(Vm[:, None], 1e-9),
                       BIG)
        oc0 = np.where(Vm[:, None] > 1e-9, np.clip(1. - ov0 / ZD, 0, 1), 0.) ** .8
        # R_flat = 2 v_z z - v, whose horizontal part is -v_h, i.e. dvec's own
        L0 = _env_menis(dvec[k, 0], dvec[k, 1], Vz)[:, None]
        L0 = L0 * (1 - oc0)[..., None] + EDGE_REFL[None, None] * oc0[..., None]
        F0v = F0 + (fresnel(Vz) - F0) * _rgh
        flat = F0v[:, None] * L0 * W_FLT[..., None]
        ex = fil - flat
        exR = ex                                  # kept for the per-term split
        # ---------------------------------------- THE TRANSMITTED COLUMN, TRACED
        # A facet at 45 deg bends the camera ray hard into the water, and where
        # this camera sees the fillet it passes 0.93-0.98 against the 0.02-0.07
        # it reflects. That column cannot be an environment lookup: the ray goes
        # somewhere specific and near, so it is traced with the file's own
        # `scene_hit` from the node's own place on the profile -- d(phi) in from
        # the waterline and z(phi) above the still level -- and the flat baseline
        # is traced from the SAME plan positions at z = 0, so the difference is
        # between two geometries and not between two shaders.
        #
        # `?` THE GEOMETRY IS ACHROMATIC: the trace uses eta = 1/IOR[1] for all
        # three channels, as the reflected column above uses one mirror
        # direction. The maps and the Fresnel are per channel. Over a leg this
        # short the three hits are microns apart, against a 3.7 mm output pixel.
        #
        # NOTE, AND IT IS NOT FIXED HERE: this column inherits `water_shade`'s
        # missing 1/n^2 radiance compression on refraction, and it must, because
        # what it is subtracting was drawn without it. Correcting it here alone
        # would put a 0.83-stop step across the junction. It is entangled with
        # LINER_TINT and EXPOSURE and is a round of its own; the README and
        # `12a` carry it. This term makes it MORE visible, not less: the
        # transmitted column now carries the waterline as well as the field.
        wl_x = hw_x[k] + gx[k] * (SLIP - s_h[k])      # the waterline point
        wl_y = hw_y[k] + gy[k] * (SLIP - s_h[k])
        nd_x = (wl_x[:, None] + mx[k][:, None] * MENIS_D[None]).ravel()
        nd_y = (wl_y[:, None] + my[k][:, None] * MENIS_D[None]).ravel()
        _eta = 1.0 / IOR[1]
        assert _eta < 1.0, 'the camera is above the water'
        _ns = MENIS_SIN[None]
        _ix = np.broadcast_to(dvec[k, 0][:, None], ndv.shape).ravel()
        _iy = np.broadcast_to(dvec[k, 1][:, None], ndv.shape).ravel()
        _iz = np.broadcast_to(dvec[k, 2][:, None], ndv.shape).ravel()
        _nx = (mx[k][:, None] * _ns).ravel()
        _ny = (my[k][:, None] * _ns).ravel()
        _nz = np.broadcast_to(MENIS_COS[None], ndv.shape).ravel()
        ttx, tty, ttz = refract(_ix, _iy, _iz, _nx, _ny, _nz, _eta)
        _pz = np.broadcast_to(MENIS_Z[None], ndv.shape).ravel()
        _g = scene_hit(nd_x, nd_y, ttx, tty, ttz, _pz)
        Lu = _menis_under(_g[0], _g[1], _g[2], _g[3], _g[4], ttz,
                          mode).reshape(ndv.shape + (3,))
        # the flat surface it replaces, traced from the same plan positions
        t0x, t0y, t0z = refract(dvec[k, 0], dvec[k, 1], dvec[k, 2],
                                np.zeros_like(Vz), np.zeros_like(Vz),
                                np.ones_like(Vz), _eta)
        _f0 = np.broadcast_to(np.ones(ndv.shape[1]), ndv.shape)
        _g0 = scene_hit(nd_x, nd_y,
                        (t0x[:, None] * _f0).ravel(), (t0y[:, None] * _f0).ravel(),
                        (t0z[:, None] * _f0).ravel(), 0.0)
        Lu0 = _menis_under(_g0[0], _g0[1], _g0[2], _g0[3], _g0[4],
                           (t0z[:, None] * _f0).ravel(),
                           mode).reshape(ndv.shape + (3,))
        filT = (1. - Ff) * Lu * W_FIL[..., None]
        flatT = (1. - F0v)[:, None] * Lu0 * W_FLT[..., None]
        exT = filT - flatT
        ex = ex + exT
        # --- the footprint kernel, folded at the wall (see the note above)
        sg = sig[k][:, None]
        dl = (d[k][:, None] - MENIS_D[None]) / sg
        dr = (d[k][:, None] + MENIS_D[None]) / sg
        K = (np.exp(-.5 * dl * dl) + np.exp(-.5 * dr * dr)) / (
            sg * np.sqrt(2. * np.pi))
        vzc = np.maximum(Vz, .05)[:, None]      # the frame's top row is 0.18
        acc = (ex * K[..., None]).sum(1) / vzc
        if parts is not None:
            # the same deposit, per term, for the diagnostic below. Costs one
            # extra reduction on the band and nothing on the frame, and it is
            # how the report says which of the two columns carries the line.
            parts['refl'][k] = (exR * K[..., None]).sum(1) / vzc
            parts['tran'][k] = (exT * K[..., None]).sum(1) / vzc
        # --- the disc, analytically. cos^n is exp(-n psi^2/2) near its peak and
        # phi sweeps the mirror direction at twice its own rate, so the integral
        # over the fillet is a Gaussian in (phi - phi*) of per-axis variance
        # 1/n + c -- c being the reflected-slope ellipse the footprint filter
        # removed, fed in through the same widening _lobe_shape applies to the
        # open water (`?` isotropic here: the fillet's own sweep is a line in
        # the same tangent space and resolving the two ellipses against each
        # other is a refinement on a term that is zero on both visible walls).
        thV = np.arctan2(Vm, Vz)
        thL = np.arctan2(Lm, SUN_DIR[2])
        phs = .5 * (thV + thL)
        nvs = np.sin(phs) * Vm + np.cos(phs) * Vz
        Rsm = 2. * nvs * np.sin(phs) - Vm
        Rsz = 2. * nvs * np.cos(phs) - Vz
        tws = -Rsm
        ds = np.interp(np.clip(phs, _mph[0], _mph[-1]), _mph, MENIS_D)
        # WHETHER THE SUN REACHES THE FACET AT ALL, taken from the incident side
        # with the file's own lip test rather than re-derived here: at the
        # mirror configuration "the mirror direction clears the coping" and "the
        # sun reaches the fillet" are the same statement, and coping_vis already
        # carries the run to the lip along the sun's azimuth AND the 0.53 deg
        # penumbra of that edge. It is evaluated at the FILLET's distance d*,
        # not at the ray's -- the shadow edge is 20 mm out on the north wall and
        # the fillet is inside 3 mm of it.
        adv = gx[k] * _SHAT[0] + gy[k] * _SHAT[1]
        run = np.where(adv > 1e-6, ds / np.maximum(adv, 1e-6), BIG)
        svis = (np.clip((run - _LRUN) / _LPEN + .5, 0, 1)
                * np.asarray(sail_vis(hw_x[k], hw_y[k]), float))
        b_ = pyh[k] ** 2 * vxx_[k] - 2 * pxh[k] * pyh[k] * vxy_[k] + pxh[k] ** 2 * vyy_[k]
        qv = 1. / N_DISC + np.maximum(2. * (_sv ** 2 + nvs * nvs * b_), 0.)
        gpk = (1. / N_DISC) / qv
        # the RESOLVED along-wall slope tilts the fillet out of its own plane,
        # so the half-vector residual is not a property of the wall alone: it is
        # where the wave field happens to carry it. That is why a real waterline
        # sparkles along a stretch rather than glinting at one point.
        nt = -(gxx_[k] * tx[k] + gyy_[k] * ty[k]) / np.sqrt(
            1. + gxx_[k] ** 2 + gyy_[k] ** 2)
        bet = (np.arcsin(np.clip(-Vt + 2. * nvs * nt, -1, 1))
               - np.arcsin(np.clip(Lt, -1, 1)))
        ea = np.sqrt(2. / qv)
        cl = .5 * (_erf((PHI_W - phs) * ea) - _erf(-phs * ea))
        Fs = F0 + (fresnel(np.clip(nvs, 1e-4, 1)) - F0) * _rgh
        amp = (np.clip(nvs, 0, None) * CAP_A * np.cos(.5 * phs)
               / np.maximum(np.sin(phs), 1e-6) * gpk * cl * svis
               * np.exp(-bet * bet / (2. * qv)) * np.sqrt(np.pi / 2.) * np.sqrt(qv))
        dsl, dsr = (d[k] - ds) / sig[k], (d[k] + ds) / sig[k]
        Kd = (np.exp(-.5 * dsl * dsl) + np.exp(-.5 * dsr * dsr)) / (
            sig[k] * np.sqrt(2. * np.pi))
        _disc = Fs * L_SUN[None] * (amp * Kd)[:, None] / vzc
        acc += _disc
        if parts is not None:
            parts['disc'][k] = _disc
        out[k] = acc
    return out


def surf_stats(x, y, fp):
    """The PAIR the footprint filter has to be consumed as, and the reason this
    is one function rather than two calls at the call site: the narrowed slope
    field, and the slope-variance tensor that was narrowed out of it. Taking the
    first without the second is the plastic-water failure; taking the second
    without the first is double counting. `fp` is the OUTPUT pixel's footprint
    on the water, `FOOT * SS`, never `FOOT`.

    `fp = None` means "no footprint", and it is guarded HERE rather than pushed
    upstream: `grad_grid` and `grad_points` both accept None, `slope_var_points`
    is the one entry point in field.py that does not, and asking for an
    interface change to satisfy one caller is the wrong way round. No footprint
    means nothing was removed, so the tensor is exactly zero -- which then runs
    through the lobe and the Fresnel term as the identity, and the whole path
    degenerates to the mirror this file had before."""
    gx, gy = grad_points(x, y, fp)
    if fp is None:
        z = np.zeros_like(gx)
        return gx, gy, z, z, z
    vxx, vyy, vxy = slope_var_points(x, y, fp)
    return gx, gy, vxx, vyy, vxy


def water_shade(hw_x, hw_y, dvec, s_h, mode, qlam, fp=None, stats=None):
    """Everything one camera ray does once it is over water: the surface normal
    from field.py, Fresnel, the sky reflection with the coping's overhang cut
    out of it, per-channel refraction INTO the pool, the traced hit, the bed /
    wall / riser maps, Beer-Lambert on the camera leg, the residual in-scatter
    and the meniscus. One function so the primary grid and the adaptive edge
    pass below are the same estimator sampled at different rates -- if they were
    two pieces of code, the refined pixels would differ from their neighbours by
    more than the sampling.

    `fp` is the output pixel's footprint on the water and `stats` is the
    already-computed `surf_stats` for these points; the primary grid passes the
    second because the disp and mono renders are the same rays and the field
    does not depend on wavelength."""
    if stats is None:
        stats = surf_stats(hw_x, hw_y, fp)
    gxx_, gyy_, vxx_, vyy_, vxy_ = stats
    nx_, ny_, nz_ = normal_from_grad(gxx_, gyy_)
    vx_, vy_, vz_ = -dvec[:, 0], -dvec[:, 1], -dvec[:, 2]
    ndv_ = np.clip(nx_ * vx_ + ny_ * vy_ + nz_ * vz_, 1e-4, 1.)
    rfx_, rfy_ = -vx_ + 2 * ndv_ * nx_, -vy_ + 2 * ndv_ * ny_
    rfz_ = np.abs(-vz_ + 2 * ndv_ * nz_)
    el = _refl_ellipse(dvec, nx_, ny_, nz_, ndv_, rfx_, rfy_, rfz_,
                       vxx_, vyy_, vxy_)
    refl_ = sky(rfx_, rfy_, rfz_, el[:5])
    fres_ = _fresnel_rough(ndv_, el[5])
    in_w = -s_h                              # distance in from the wall face
    egx_, egy_, _ = pool_grad(hw_x, hw_y)
    toward = rfx_ * egx_ + rfy_ * egy_       # + = reflected ray heads at the wall
    over = rfz_ * np.maximum(in_w + SLIP, 0.) / np.maximum(toward, 1e-6)
    occ_ = np.where(toward > 0, np.clip(1. - over / ZD, 0, 1), 0.) ** .8
    refl_ = refl_ * (1 - occ_)[:, None] + EDGE_REFL[None] * occ_[:, None]
    lip_ao = 1. - .34 * np.exp(-(in_w + SLIP) / .045)
    mnis_ = meniscus(hw_x, hw_y, s_h, dvec, fp, gxx_, gyy_, vxx_, vyy_, vxy_,
                     mode)

    water = np.zeros((hw_x.size, 3))
    geo, smG_ = {}, None
    sidG = uG = vG = cylG = None
    keyc = np.zeros(hw_x.size, np.int32)      # what EACH channel saw, packed
    for c in range(3):
        key = c if mode == 'disp' else 0
        if key not in geo:
            # 'disp' gives every ray its own wavelength inside the channel's
            # band; 'mono' is one wavelength for all three, so one trace serves
            # them and the A/B carries no dispersion at all.
            if mode == 'disp':
                eta = 1.0 / n_water(BAND[c, 0] + qlam * (BAND[c, 1] - BAND[c, 0]))
            else:
                eta = 1.0 / IOR[1]
            # The camera looks DOWN into the water: eta = 1/n(lambda) < 1 for
            # every wavelength in every band, so refract() cannot return its TIR
            # null here. This is the call site the README's underwater pass will
            # reuse with eta > 1, where it can and must -- hence the assert
            # rather than a comment, on one scalar per channel.
            assert np.all(eta < 1.0), 'the camera is above the water'
            tx, ty, tz = refract(dvec[:, 0], dvec[:, 1], dvec[:, 2],
                                 nx_, ny_, nz_, eta)
            geo[key] = scene_hit(hw_x, hw_y, tx, ty, tz) + (tz,)
        sid, u, v, sm, cyl, tz = geo[key]
        col = np.zeros(len(u))
        bi, wim = bed_img[mode], wall_img[mode]
        m = sid == 0
        if m.any():
            col[m] = sample(bi[..., c:c + 1], u[m], v[m], X0, X1, Y0, Y1)[:, 0]
        for wi, sv in enumerate((1, 2, 3, 4)):
            m = sid == sv
            if m.any():
                a, b = (Y0, Y1) if sv <= 2 else (X0, X1)
                col[m] = sample(wim[wi][..., c:c + 1], u[m], v[m],
                                a, b, -DEPTH, 0.)[:, 0]
        m = sid == 5
        if m.any():
            col[m] = _riser_shade(u[m], v[m], tz[m] * sm[m], cyl[m], c, mode)
        water[:, c] = col * np.exp(-ABS[c] * sm)
        # The three channels see the silhouette in three PLACES -- measured at
        # 2.07 output pixels apart -- so a pixel can be clean in green and cut
        # by the edge in red. Flagging on green alone would leave those unfixed,
        # and they are the ones that come out coloured. Packed here at no cost:
        # the traces are already done.
        keyc += (sid.astype(np.int32) * 8 + (cyl.astype(np.int32) + 1)) * (64 ** c)
        if c == 1:
            smG_, sidG, uG, vG, cylG = sm, sid, u, v, cyl
    # the residual in-scatter of a treated pool: tiny, but it is a PATH integral,
    # so it grows with the water actually crossed and is one more depth cue.
    water += np.array([.002, .011, .019])[None] * (1 - np.exp(-.30 * smG_))[:, None]
    water *= lip_ao[:, None]
    spec_ = fres_ * refl_
    tran_ = (1 - fres_) * water
    # The meniscus is a correction to BOTH columns and it is allowed to be
    # negative -- on a wall seen at 11 deg grazing the flat surface reflects the
    # undercut at F = 0.36 while the fillet turns its facets toward the eye and
    # reflects the sky at F = 0.02, and the fillet's reflected half is then the
    # DARKER of the two. It cannot take away more than the columns it is
    # correcting, and that is the only clamp on it. The floor moved from -spec_
    # to -(spec_ + tran_) when the transmitted half was built: clamping the sum
    # of two corrections against one of the two columns would have made the
    # clamp bind on the transmitted excess, which is the larger and the positive
    # one, and turned a floor into a ceiling on the wrong term.
    out = spec_ + tran_ + np.maximum(mnis_, -(spec_ + tran_))
    # the two halves are carried out separately as luminances so that spec C can
    # be judged on the right one. "A compact patch of isolated bright points" is
    # a statement about the REFLECTED term; if the transmitted bed beats it
    # everywhere, no amount of glint-density contrast will show, and that is a
    # measurement rather than an opinion. Luminance only -- the full pair would
    # be 300 MB on this ray count for a number that is a scalar.
    _Y = np.array([.2126, .7152, .0722])
    return (out, sidG, uG, vG, smG_, cylG, occ_, keyc, spec_ @ _Y, tran_ @ _Y)


# ------------------------------------------ THE LINE, MEASURED BEFORE IT IS DRAWN
# Every claim the block above makes is checkable off the same function the
# picture is made with: probe a waterline point with a fan of rays running in
# from the wall, and read the profile the pixel grid will actually receive.
def _menis_probe(P, nd=401, span=.060, still=False):
    """(peak radiance, FWHM in OUTPUT pixels, the integral I(v), the footprint
    across the waterline, and where the point lands in the frame).

    `still=True` hands `meniscus` a zero RESOLVED slope, which is the only way to
    read the sun's branch at its own maximum: with the wave field in, the
    half-vector residual is where the waves happen to carry it and the crossing
    computed from the mean surface is not where the glint actually lands."""
    P = np.asarray(P, float)
    gx, gy, _ = pool_grad(P[0], P[1])
    px = P[0] - gx * np.linspace(0., span, nd)
    py = P[1] - gy * np.linspace(0., span, nd)
    dd = np.linspace(0., span, nd)
    dv = np.stack([px, py, np.zeros(nd)], 1) - EYE[None]
    tt = np.linalg.norm(dv, axis=1)
    dv /= tt[:, None]
    fpp = tt * PIXANG / np.maximum(np.abs(dv[:, 2]), .10) * SS
    st = surf_stats(px, py, fpp)
    if still:
        st = (np.zeros(nd), np.zeros(nd)) + st[2:]
    pt = {n: np.zeros((nd, 3)) for n in ('refl', 'tran', 'disc')}
    Lc = meniscus(px, py, SLIP - dd, dv, fpp, *st, parts=pt)
    y = Lc[:, 1]
    dh = np.maximum(np.hypot(dv[:, 0], dv[:, 1]), 1e-9)
    pm = (dv[:, 0] * -gx + dv[:, 1] * -gy) / dh
    qm = (-dv[:, 1] * -gx + dv[:, 0] * -gy) / dh
    w_m = fpp * np.sqrt(pm * pm + (qm * dv[:, 2]) ** 2)
    ipk = int(np.argmax(np.abs(y)))
    half = np.abs(y) >= .5 * abs(y[ipk])
    fw = (np.flatnonzero(half)[-1] - np.flatnonzero(half)[0] + 1) * (span / (nd - 1))
    _I = lambda a: float((a[:, 1] * -dv[:, 2]).sum() * span / (nd - 1))
    return (y[ipk], fw / max(w_m[ipk], 1e-9), _I(Lc),
            w_m[0], project(P)[0], dd[ipk], Lc[ipk],
            (_I(pt['refl']), _I(pt['tran']), _I(pt['disc'])))


_WLL = (("east ", np.array([1., 0.]), np.array([X1, 0.])),
        ("north", np.array([0., 1.]), np.array([0., Y1])),
        ("west ", np.array([-1., 0.]), np.array([X0, 0.])),
        ("south", np.array([0., -1.]), np.array([0., Y0])))
print("THE MENISCUS LINE, per wall. `m` is the poolward horizontal. The sun's own "
      "line needs BOTH  (a) L.m > 0, or its mirror direction leaves under the "
      "coping,  and (b) the half-vector residual beta = asin(-v.t) - asin(L.t) to "
      "pass through zero on a stretch the frame can see:")
for _nm, _no, _o0 in _WLL:
    _m = -_no
    _t = np.array([-_no[1], _no[0]])
    _Lm = SUN_DIR[:2] @ _m
    _Lt = SUN_DIR[:2] @ _t
    _u = np.linspace(.03, (Y1 - Y0 if abs(_no[0]) > 0 else X1 - X0) - .03, 600)
    _P = (np.stack([np.full_like(_u, _o0[0]), _u], 1) if abs(_no[0]) > 0
          else np.stack([_u, np.full_like(_u, _o0[1])], 1)) + _no[None] * SLIP
    _V = EYE[None, :2] - _P
    _Vn = np.linalg.norm(np.concatenate([_V, np.full((len(_u), 1), EYE[2])], 1), axis=1)
    _Vt = (_V @ _t) / _Vn
    _bet = np.degrees(np.arcsin(np.clip(-_Vt, -1, 1))
                      - np.arcsin(np.clip(_Lt, -1, 1)))
    _pp = project(np.concatenate([_P, np.zeros((len(_u), 1))], 1))
    _inf = ((_pp[:, 0] >= 0) & (_pp[:, 0] < W // SS) &
            (_pp[:, 1] >= 0) & (_pp[:, 1] < H // SS))
    _cr = np.flatnonzero(np.diff(np.sign(_bet)) != 0)
    _cs = ("beta = 0 at %s, %s frame"
           % (np.round(_P[_cr[0]], 2), "IN" if _inf[_cr[0]] else "out of")
           ) if _cr.size else "beta never reaches 0 on this wall"
    print("   %s wall: L.m = %+.3f -> the sun is %s, so its disc is %-9s | %s | "
          "%3.0f%% of the waterline is in frame"
          % (_nm, _Lm, "POOLWARD" if _Lm > 0 else "behind the wall",
             "REACHABLE" if _Lm > 0 else "OCCLUDED", _cs, 100 * _inf.mean()))
print("   -- and the coping-shadow print at the top of the file says the same "
      "thing from the incident side: the lip shades the fillet on exactly the "
      "walls whose L.m < 0.")
print("   the line itself, probed with the render's own `meniscus` along the "
      "waterlines this frame can see:")
for _nm, _pts in (("north", [(x, Y1 + SLIP) for x in (0.4, 1.4, 2.4, 3.4, 4.4, 5.4, 6.4, 7.3)]),
                  ("west ", [(X0 - SLIP, y) for y in (3.5, 3.9)]),
                  ("east ", [(X1 + SLIP, y) for y in (2.09, 2.6, 3.2)])):
    for _p in _pts:
        _P3 = np.array([_p[0], _p[1], 0.])
        _pk, _fw, _I, _w, _px, _dpk, _c3, _sp = _menis_probe(_P3)
        _rr = np.linalg.norm(EYE - _P3)
        print("     %s (%.2f, %.2f) %.2f m  px(%4.0f,%4.0f)%s  footprint %5.2f mm "
              "| peak %+8.4f at d = %.2f mm, %.2f output px wide | I = %+.3e "
              "= refl %+.2e + tran %+.2e + disc %+.2e W/sr/m | rgb %s"
              % (_nm, _p[0], _p[1], _rr, _px[0], _px[1],
                 "  " if (0 <= _px[0] < W // SS and 0 <= _px[1] < H // SS) else " *",
                 1000 * _w, _pk, 1000 * _dpk, _fw, _I, _sp[0], _sp[1], _sp[2],
                 np.round(_c3, 4)))
print("     (* = outside the frame.  The east waterline is in the frame's plan "
      "but not in its picture: the near coping's own arris stands in front of "
      "it, which is why the sun's line -- reachable there and nowhere else in "
      "shot -- cannot be seen.)")
# What the ambient lift this replaces was worth, in the same units: it was
# (SKY_AMB*0.17 + SUN_COL*0.006) with an exp(-d/2a) profile, so its flux per
# unit of waterline is that times 2a times v_z, and the ratio is the price of
# the guess.
# WHAT THE SUN'S BRANCH IS WORTH where it is reachable, so that the half of this
# term which this frame cannot show is priced rather than left as dead code. The
# probe is run on the EAST wall at its own beta = 0, with the resolved wave slope
# taken out -- with it in, the residual is wherever the waves carry it, which is
# what makes a real waterline sparkle along a stretch instead of glinting at one
# point, and is why the probe a few centimetres away reads nothing.
_esun = np.array([X1 + SLIP, 2.09, 0.])
_pk_s, _fw_s, _I_s, _w_s, _px_s, _d_s, _c_s, _sp_s = _menis_probe(
    _esun, still=True)
print("   the SUN's branch, priced where it is reachable -- east wall at its own "
      "beta = 0, (%.2f, %.2f), with the resolved wave slope taken out: I = %.3e "
      "W/sr/m, peak %.1f at d = %.2f mm, which is %.1fx this file's white point "
      "of %.1f. It is behind the near coping's arris in this frame (the ray that "
      "grazes that arris meets the water %.0f mm out from the wall), so what the "
      "picture can show of the meniscus is the horizon's branch alone."
      % (_esun[0], _esun[1], _I_s, _pk_s, 1000 * _d_s, _pk_s / L_WHITE,
         L_WHITE, 1000 * (ZD * (EYE[0] - X1 - SBUL) / (EYE[2] - ZD)
                          - (SBUL - SLIP))))
_pmid = np.array([2.4, Y1 + SLIP, 0.])
_vzm = abs((EYE - _pmid)[2] / np.linalg.norm(EYE - _pmid))
_amb = (SKY_AMB * .17 + SUN_COL * .006) * MENIS_W * _vzm
print("   the AMBIENT lift this replaces was worth %s W/sr/m per unit of "
      "waterline at x = 2.4 on the north wall (and the same everywhere, since it "
      "knew about neither the sun nor the eye). The derived integral there is "
      "%.3e in green, so the guess carried %.1fx the flux the physics has -- and "
      "carried it flat, where the physics puts nearly all of it at the far end, "
      "where the mirror direction passes closest to the sun."
      % (np.round(_amb, 4), _menis_probe(_pmid)[2],
         _amb[1] / max(_menis_probe(_pmid)[2], 1e-12)))


import sys; sys.stdout.flush(); sys.exit(0)
