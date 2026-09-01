#!/usr/bin/env python3
"""Recompute every number in this directory's README.md from the JPEGs beside it.

Nothing here is read off a published figure. Each row is derived from the stored
file, and the stored file is a Wikimedia thumbnail whose URL the README records,
so a reader can re-fetch the bytes and re-run this.

Two conventions, stated once because the rest of the file depends on them:

  * "luma8" is Rec.709 luma computed on the *stored 8-bit sRGB code values*.
    It is not luminance and it is not linear light. It is used where the
    quantity of interest is a spread or a texture statistic, which is what the
    code values carry.
  * "linY" inverts the sRGB EOTF first. That recovers DISPLAY-REFERRED linear,
    not scene-referred linear. Every ratio taken on it is therefore a bound,
    and the README says in which direction for each pair.

Run: python3 measure.py            (numpy + Pillow, nothing else)
"""
import math
import numpy as np
from PIL import Image
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def img(name):
    return Image.open(os.path.join(HERE, name)).convert('RGB')


def luma8(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def boxcar(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same')


# ---------------------------------------------------------------- glitter ---

def glitter_bands(name, y0, y1, nb, centre, half=170, core=10):
    """Per band: half-max width of the row-averaged cross-path profile, and the
    luma statistics of a +/- `core` px strip on the path centre."""
    L = luma8(np.asarray(img(name)).astype(np.float64))
    H, W = L.shape
    print(f"\n=== {name}  stored {W}x{H} — glitter path, banded")
    print(f"{'band rows':>13}{'ctr x':>7}{'halfmax W':>10}{'% frame':>8}"
          f"{'core mean':>10}{'core sd':>9}{'core p5':>9}{'core>=250%':>11}")
    edges = np.linspace(y0, y1, nb + 1).astype(int)
    for i in range(nb):
        a, b = edges[i], edges[i + 1]
        prof = np.zeros(2 * half + 1)
        n = 0
        for r in range(a, b):
            c = int(round(centre(r)))
            if c - half < 0 or c + half >= W:
                continue
            prof += L[r, c - half:c + half + 1]
            n += 1
        prof /= max(n, 1)
        bg = np.median(np.concatenate([prof[:40], prof[-40:]]))
        pk = prof[half - 3:half + 4].max()
        hm = bg + 0.5 * (pk - bg)
        l = half
        while l > 0 and prof[l] > hm:
            l -= 1
        rr = half
        while rr < 2 * half and prof[rr] > hm:
            rr += 1
        strip = np.concatenate([L[r, max(0, int(round(centre(r))) - core):
                                     int(round(centre(r))) + core + 1]
                                for r in range(a, b)])
        print(f"{a:6d}-{b:<6d}{int(round(centre((a + b) // 2))):7d}{rr - l:10d}"
              f"{100 * (rr - l) / W:8.1f}{strip.mean():10.1f}{strip.std():9.1f}"
              f"{np.percentile(strip, 5):9.1f}{100 * (strip >= 250).mean():11.1f}")


# --------------------------------------------------- texture: runs and acf ---

def texture(name, regions, note=''):
    """Above-half-max run/gap lengths along image rows, and the 1/e lag of the
    row autocorrelation of high-pass luma. Both in pixels. `l/W` is the
    correlation length as a percentage of the region's own width — the one
    figure here that needs no scale at all."""
    L = luma8(np.asarray(img(name)).astype(np.float64))
    print(f"\n=== {name} — texture{(' — ' + note) if note else ''}")
    print(f"{'region':38s}{'W px':>6}{'thr':>6}{'cov%':>7}{'run med':>9}"
          f"{'run q90':>9}{'gap med':>9}{'acf 1/e':>9}{'l/W %':>8}")
    for lab, (x0, y0, x1, y1) in regions.items():
        P = L[y0:y1, x0:x1]
        bg, pk = np.percentile(P, 10), np.percentile(P, 99)
        thr = bg + 0.5 * (pk - bg)
        m = P > thr
        runs, gaps = [], []
        for r in range(m.shape[0]):
            c = g = 0
            for v in m[r]:
                if v:
                    if g:
                        gaps.append(g); g = 0
                    c += 1
                else:
                    if c:
                        runs.append(c); c = 0
                    g += 1
            if c:
                runs.append(c)
        runs = np.array(runs) if runs else np.array([0])
        gaps = np.array(gaps) if gaps else np.array([0])
        # autocorrelation of high-pass luma along rows
        hp, W = 61, x1 - x0
        trim = hp // 2
        maxlag = max(4, min(80, (W - 2 * trim) // 3))
        acc = np.zeros(maxlag + 1); n = 0
        for r in range(P.shape[0]):
            row = P[r] - boxcar(P[r], hp)
            row = row[trim:W - trim]
            if row.size < maxlag + 4:
                continue
            row = row - row.mean()
            v = (row * row).mean()
            if v <= 0:
                continue
            acc += np.array([(row[:row.size - k] * row[k:]).mean() / v
                             for k in range(maxlag + 1)])
            n += 1
        l1 = float('nan')
        if n:
            acc /= n
            for k in range(1, maxlag + 1):
                if acc[k] <= 1 / math.e:
                    l1 = k - 1 + (acc[k - 1] - 1 / math.e) / max(acc[k - 1] - acc[k], 1e-9)
                    break
        print(f"{lab:38s}{W:6d}{thr:6.0f}{100 * m.mean():7.1f}"
              f"{np.percentile(runs, 50):9.1f}{np.percentile(runs, 90):9.1f}"
              f"{np.percentile(gaps, 50):9.1f}{l1:9.1f}{100 * l1 / W:8.2f}")


# ------------------------------------------------------------- radiometry ---

def surfaces(name, regions, note=''):
    a = np.asarray(img(name)).astype(np.float64)
    print(f"\n=== {name}  {a.shape[1]}x{a.shape[0]} — surfaces"
          f"{(' — ' + note) if note else ''}")
    print(f"{'surface':32s}{'sRGB mean R,G,B':24s}{'luma8':>7}{'sd':>6}"
          f"{'linY':>9}{'linR/B':>8}{'linG/B':>8}")
    for lab, (x0, y0, x1, y1) in regions.items():
        s = a[y0:y1, x0:x1]
        L = luma8(s)
        lin = srgb_to_linear(s)
        R, G, B = lin[..., 0].mean(), lin[..., 1].mean(), lin[..., 2].mean()
        print(f"{lab:32s}"
              + f"({s[...,0].mean():5.1f},{s[...,1].mean():5.1f},{s[...,2].mean():5.1f})".ljust(24)
              + f"{L.mean():7.1f}{L.std():6.1f}{0.2126*R+0.7152*G+0.0722*B:9.4f}"
                f"{R/B:8.3f}{G/B:8.3f}")


# ------------------------------------------- matched-luminance chromaticity -

def matched_luminance(name, box_a, box_b, lab_a, lab_b, windows):
    """Compare the chromaticity of two regions RESTRICTED TO PIXELS OF THE SAME
    display-referred luminance.

    Why this and not a plain box mean. In these frames G/B rises with brightness
    everywhere, including inside a single water region with no foam in it — the
    tone curve and the sun/sky mix couple level to chromaticity. So a difference
    in mean G/B between a bright region and a dark one proves nothing. Matching
    luminance first removes the coupling and leaves the bar's own surviving
    instrument: a within-frame ratio between surfaces close in level.
    """
    a = np.asarray(img(name)).astype(np.float64)

    def stats(box, lo, hi):
        x0, y0, x1, y1 = box
        s = a[y0:y1, x0:x1].reshape(-1, 3)
        L = srgb_to_linear(s)
        Y = 0.2126 * L[:, 0] + 0.7152 * L[:, 1] + 0.0722 * L[:, 2]
        m = (Y >= lo) & (Y < hi)
        if m.sum() < 200:
            return None
        return m.sum(), Y[m].mean(), (L[m, 1] / L[m, 2]).mean(), (L[m, 0] / L[m, 2]).mean()

    print(f"\n=== {name} — chromaticity at matched luminance")
    print(f"    A = {lab_a}\n    B = {lab_b}")
    print(f"{'linY window':>16}{'nA':>8}{'G/B A':>8}{'nB':>9}{'G/B B':>8}{'A/B':>8}")
    for lo, hi in windows:
        ra, rb = stats(box_a, lo, hi), stats(box_b, lo, hi)
        if not ra or not rb:
            print(f"{lo:.2f}-{hi:.2f}".rjust(16) + "   too few pixels")
            continue
        print(f"{lo:.2f}-{hi:.2f}".rjust(16)
              + f"{ra[0]:8d}{ra[2]:8.3f}{rb[0]:9d}{rb[2]:8.3f}{ra[2]/rb[2]:8.3f}")


# ------------------------------------------------------- angular scale -----

def angular_scale(name, focal35_mm, stored_w, path_offset_px, widths_px, note):
    """Degrees per stored pixel at a given offset from the frame centre, from
    the EXIF focal length. A width in pixels is meaningless across two frames
    shot at 105 mm and at 27 mm equivalent; this is what makes them comparable.

    Assumes the published file is the full frame. Both g1 and g2 are within 3%
    of their sensors' native pixel dimensions, so the crop is negligible here.
    A rectilinear lens is assumed; barrel distortion at 27 mm eq. is a further
    unquantified error on g2, in the direction of understating the wide end.
    """
    f_px = (stored_w / 2) / math.tan(math.radians(
        math.degrees(2 * math.atan(18.0 / focal35_mm)) / 2))
    dtheta = math.degrees(f_px / (f_px ** 2 + path_offset_px ** 2))
    print(f"\n{name}: focal {focal35_mm:.0f} mm eq, stored width {stored_w} px "
          f"-> f = {f_px:.0f} px; at {path_offset_px:+d} px from centre, "
          f"{dtheta:.5f} deg/px")
    print(f"  {note}")
    for w in widths_px:
        print(f"    path width {w:4d} px  ->  {w * dtheta:6.3f} deg")


def angular_table():
    print("\n=== glitter path width in ANGLE, not pixels")
    angular_scale('g1', 105.0, 1280, -70, [38, 75],
                  'Canon 5D IV, full frame, 105 mm; path near frame centre')
    angular_scale('g2', 27.0, 1280, 350, [77, 138],
                  'Nikon D300 DX, 18 mm = 27 mm eq; path right of centre')


# ---------------------------------------------------------- solar position ---

def julian_day(y, m, d, h, mi, s):
    if m <= 2:
        y -= 1; m += 12
    A = y // 100
    B = 2 - A + A // 4
    return (int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
            + (h + mi / 60 + s / 3600) / 24.0)


def sun_position(y, mo, d, h, mi, s, lat, lon):
    """NOAA / Meeus low order, Bennett refraction. UTC in, (elevation, azimuth
    from north) out, both degrees. Same recipe the frozen bar used on its own
    frames, so the two are comparable."""
    J = julian_day(y, mo, d, h, mi, s)
    T = (J - 2451545.0) / 36525.0
    L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    Mr = math.radians(M)
    C = ((1.914602 - T * (0.004817 + 0.000014 * T)) * math.sin(Mr)
         + (0.019993 - 0.000101 * T) * math.sin(2 * Mr)
         + 0.000289 * math.sin(3 * Mr))
    om = 125.04 - 1934.136 * T
    app = L0 + C - 0.00569 - 0.00478 * math.sin(math.radians(om))
    e0 = 23 + (26 + (21.448 - T * (46.8150 + T * (0.00059 - T * 0.001813))) / 60) / 60
    e = e0 + 0.00256 * math.cos(math.radians(om))
    er, ar = math.radians(e), math.radians(app)
    dec = math.degrees(math.asin(math.sin(er) * math.sin(ar)))
    yv = math.tan(math.radians(e / 2)) ** 2
    eo = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    E = 4 * math.degrees(
        yv * math.sin(2 * math.radians(L0)) - 2 * eo * math.sin(Mr)
        + 4 * eo * yv * math.sin(Mr) * math.cos(2 * math.radians(L0))
        - 0.5 * yv * yv * math.sin(4 * math.radians(L0))
        - 1.25 * eo * eo * math.sin(2 * Mr))
    tst = ((h + mi / 60 + s / 3600) * 60 + E + 4 * lon) % 1440
    ha = tst / 4 - 180
    lar, dr, har = math.radians(lat), math.radians(dec), math.radians(ha)
    cz = max(-1, min(1, math.sin(lar) * math.sin(dr)
                     + math.cos(lar) * math.cos(dr) * math.cos(har)))
    el = 90 - math.degrees(math.acos(cz))
    R = 1.02 / math.tan(math.radians(el + 10.3 / (el + 5.11))) / 60 if el > -1 else 0
    az = math.degrees(math.atan2(-math.sin(har),
                                 math.tan(dr) * math.cos(lar)
                                 - math.sin(lar) * math.cos(har))) % 360
    return el + R, az


SOLAR = [
    # slug, UTC y m d h mi s, lat, lon, how the UTC was obtained
    ("g1", 2024, 7, 29, 19, 8, 36, 54.154827, 11.762102,
     "EXIF 21:08:36 + EXIF GPS; assumed CEST (UTC+2)"),
    ("g2", 2013, 1, 4, 20, 45, 13, 10.874759, -64.053718,
     "EXIF 16:15:13 + EXIF GPS; assumed VET (UTC-4:30, in force 2007-2016)"),
    ("f1", 2014, 10, 26, 16, 19, 43, 37.8553, -8.7919,
     "EXIF 16:19:43; assumed WET (UTC+0, DST ended 26 Oct 2014); coords INFERRED from the place name, not EXIF"),
    ("f2", 2010, 3, 13, 16, 55, 41, 37.8553, -8.7919,
     "EXIF 16:55:41; assumed WET (UTC+0, DST began 28 Mar 2010); coords INFERRED from the place name, not EXIF"),
    ("s1", 2018, 12, 24, 21, 21, 43, 27.055961, -82.442464,
     "EXIF 16:21:43 + EXIF GPS; assumed EST (UTC-5)"),
    ("b1", 2025, 4, 2, 23, 30, 13, 13.174355, -88.167564,
     "EXIF 17:30:13 + EXIF GPS; assumed CST (UTC-6)"),
    ("b2", 2016, 12, 4, 0, 20, 3, 37.991378, -122.972403,
     "EXIF 16:20:03 + EXIF GPS; assumed PST (UTC-8)"),
    ("r1", 2025, 5, 17, 11, 55, 4, 54.116328, -0.124833,
     "EXIF 12:55:04 + EXIF GPS; assumed BST (UTC+1)"),
]


def solar_table():
    print("\n=== derived solar geometry (NOAA/Meeus + Bennett refraction)")
    print("Every row depends on a timezone ASSUMPTION and on the camera clock "
          "being right.\nCheck it against the shadows in the frame before "
          "trusting it.")
    print(f"{'':5s}{'elev':>8}{'azim':>9}  provenance")
    for slug, y, mo, d, h, mi, s, la, lo, note in SOLAR:
        el, az = sun_position(y, mo, d, h, mi, s, la, lo)
        print(f"{slug:5s}{el:8.2f}{az:9.2f}  {note}")


# ------------------------------------------------------------------- main ---

if __name__ == '__main__':
    glitter_bands('g1-glitter-lowsun-baltic.jpg', 333, 612, 6,
                  centre=lambda r: 565 + (r - 335) * 0.05)
    glitter_bands('g2-glitter-highsun-bay.jpg', 478, 848, 6,
                  centre=lambda r: 968 + (r - 485) * 0.09)

    texture('g1-glitter-lowsun-baltic.jpg', {
        'path band 333-379 (near horizon)': (500, 333, 650, 379),
        'path band 426-472 (mid)':          (500, 426, 660, 472),
        'path band 565-612 (near field)':   (500, 565, 670, 612),
        'off-path water (control)':         (200, 430, 400, 520)})
    texture('g2-glitter-highsun-bay.jpg', {
        'path band 478-539 (near horizon)': (880, 478, 1100, 539),
        'path band 663-724 (mid)':          (890, 663, 1110, 724),
        'path band 786-848 (near field)':   (900, 786, 1120, 848),
        'off-path water (control)':         (400, 700, 700, 820)})
    texture('f2-swash-foam-lace.jpg', {
        'stranded lace over wet sand':      (560, 540, 1060, 640),
        'thin foam sheet on backwash':      (460, 690, 960, 800),
        'thick bore whitewater':            (180, 740, 560, 880),
        'dry sand (resolution floor)':      (900, 60, 1500, 180)},
        'scale 71 px/m alongshore, see README')
    texture('f1-breaker-three-whites.jpg', {
        'sunlit bore, right of centre':     (1150, 470, 1650, 620),
        'swash foam near the bather':       (1250, 830, 1750, 960),
        'shadowed bore, left of centre':    (300, 540, 800, 680),
        'unbroken water offshore':          (200, 60, 800, 280)},
        'scale 78 px/m alongshore, see README')

    surfaces('s1-wetdry-nadir.jpg', {
        'sea, shallow over sand':     (850, 150, 1200, 350),
        'sea, over dark rock':        (300, 120, 480, 230),
        'wet sand band':              (250, 555, 650, 600),
        'dry sand':                   (630, 655, 870, 715)},
        'nadir, so no obliquity; sun 14.9 deg')
    surfaces('f2-swash-foam-lace.jpg', {
        'dry sand, upper beach':      (900, 60, 1500, 180),
        'sand same row, x1100-1500':  (1100, 400, 1500, 450),
        'sand same row, x220-520':    (220, 400, 520, 450),
        'saturated sand, swash zone': (700, 500, 1000, 545),
        'wave face, green (lower L)': (40, 900, 200, 1010)},
        'the x1100-1500 / x220-520 pair is same-row: same range, same slope, same light')
    surfaces('f1-breaker-three-whites.jpg', {
        'sunlit bore':                (1200, 480, 1600, 600),
        'shadowed bore':              (320, 560, 720, 680),
        'swash foam deck':            (1300, 850, 1700, 950),
        'green window in the crest':  (800, 505, 960, 570),
        'unbroken water offshore':    (250, 80, 750, 240),
        'dry sand':                   (1150, 1190, 1600, 1280),
        'wet sand under a film':      (500, 1050, 900, 1130)})
    surfaces('b1-headland-refraction.jpg', {
        'deep water offshore':        (900, 60, 1250, 220),
        'water outside the surf':     (830, 330, 1000, 430),
        'white surf band':            (760, 150, 900, 260)},
        'NOTE the red channel: this frame is post-processed and its colour is not usable')
    surfaces('b2-embayed-colour-ladder.jpg', {
        'deep water, bay behind':     (1250, 380, 1750, 470),
        'open sea, offshore left':    (60, 600, 300, 720),
        'nearshore, aerated':         (450, 880, 700, 970),
        'surf':                       (600, 860, 900, 960),
        'wet sand (lower beach)':     (1000, 950, 1150, 1060),
        'dry sand (upper beach)':     (1150, 780, 1350, 880)},
        'STITCHED PANORAMA with flare across the left third; see README')

    matched_luminance('f1-breaker-three-whites.jpg',
                      (800, 505, 960, 570), (250, 80, 750, 240),
                      'thin backlit crest window',
                      'deep unbroken water, same exposure',
                      [(0.24, 0.30), (0.26, 0.32), (0.28, 0.34)])

    angular_table()
    solar_table()
