"""External checks on this skill's own arithmetic.

    python3 validate_terrain.py        # exits non-zero on any FAIL
    python3 validate_terrain.py -v     # also prints every tolerance's reason
    python3 validate_terrain.py --bugs # re-run the suite once per deliberately
                                       # reintroduced defect, and print which
                                       # rows caught each one

WHY THIS FILE EXISTS. Chapter `11` is this skill's review chapter: it tells the
reader to specify debug views and worst-case tests BEFORE implementation, and
lists fourteen ways a verification fails while looking like one. For twenty
chapters, none of that was applied to the skill itself. Its numbers were
reached by hand and read by nobody twice -- and one of them, chapter `06`'s
ring-residency column, was wrong by fifty tiles until somebody added it up.

WHAT THIS SUITE CAN AND CANNOT SEE. There is no GPU here, so nothing about
throughput, bandwidth or driver behaviour is testable and none is claimed. What
IS testable is every statement of the form "this quantity equals that
expression", and that is most of what a LOD controller, a crack contract, a
residency budget and a case table are made of. Those are also the statements
whose errors are silent: a screen-space error off by a factor of two still
draws a picture, and a case table with one wrong entry still meshes 255
configurations correctly.

THE THREE TIERS, and the tier is the strength of the evidence:

  Tier 1  CLOSED FORM.   The answer is known analytically or combinatorially;
                         a disagreement is a bug in one of the two.
  Tier 2  PUBLISHED.     Compared against a figure this domain agrees on. A
                         disagreement may be a bug or a different convention,
                         and the row says which conventions it assumes.
  Tier 3  INDEPENDENT.   Two methods that share no line, so a disagreement
                         localises to one of them.

⚠️ EVERY TOLERANCE IS JUSTIFIED FROM THE ESTIMATOR'S OWN ERROR, never from the
disagreement it reports. A tolerance widened until a row passes has converted a
finding into a decoration, and `-v` prints each justification so that move is
visible in the diff.
"""
import math
import sys

import numpy as np

import budget as B                                              # noqa: E402
import lod as L                                                 # noqa: E402
import tables as T                                              # noqa: E402


class Row(object):
    __slots__ = ('tier', 'name', 'exp', 'got', 'tol', 'status', 'why', 'unit')

    def __init__(self, tier, name, exp, got, tol, status, why, unit):
        self.tier, self.name, self.exp, self.got = tier, name, exp, got
        self.tol, self.status, self.why, self.unit = tol, status, why, unit


ROWS = []
BUGS = {}


def _fmt(v):
    if isinstance(v, float):
        return '%.6g' % v
    if isinstance(v, (list, tuple, np.ndarray)):
        a = np.asarray(v).reshape(-1)
        return '[' + ' '.join('%.6g' % x for x in a[:4]) + (
            ' ...' if a.size > 4 else '') + ']'
    return str(v)


def check(tier, name, got, exp, tol, why, unit='', rel=False):
    """A comparison with a stated tolerance and a stated reason for it."""
    g, e = np.asarray(got, float), np.asarray(exp, float)
    # A ROW COMPUTED ON NOTHING IS THE WORST KIND OF GREEN. `np.all([])` is
    # True, so a selection that matched nothing passes silently; the sibling
    # water suite shipped two of those on its first run. An empty comparison is
    # an error here, never a pass.
    if g.size == 0 or e.size == 0:
        raise AssertionError('row "%s" compares an EMPTY selection -- a mask '
                             'that matched nothing is a blind test, not a '
                             'passing one' % name)
    lim = np.asarray(tol, float) * (np.abs(e) if rel else 1.0)
    ok = bool(np.all(np.abs(g - e) <= lim + 1e-300))
    ROWS.append(Row(tier, name, exp, got, ('%s rel' % _fmt(tol)) if rel else tol,
                    'PASS' if ok else 'FAIL', why, unit))
    return ok


def between(tier, name, got, lo, hi, why, unit=''):
    g = float(got)
    ROWS.append(Row(tier, name, '%s..%s' % (_fmt(lo), _fmt(hi)), got, 'range',
                    'PASS' if lo <= g <= hi else 'FAIL', why, unit))
    return lo <= g <= hi


def info(tier, name, got, note, exp=None):
    ROWS.append(Row(tier, name, exp, got, '-', 'INFO', note, ''))


# ==========================================================================
#  A · SCREEN-SPACE ERROR, THE CURRENCY
# ==========================================================================
def _sec_sse():
    H, FOV = 1080, math.radians(60.0)

    # The projection identity, against a direct trigonometric construction that
    # shares no line with it: place a segment of length eps perpendicular to the
    # view axis at distance d, project both endpoints through the same frustum
    # by hand, and measure the pixel span.
    d = np.array([10.0, 50.0, 200.0, 1000.0])
    eps = 0.25
    half_world = d * math.tan(0.5 * FOV)
    by_hand = eps / half_world * (0.5 * H)
    check(1, 'screen-space error against a hand-projected segment',
          L.screen_space_error(eps, H, FOV, d), by_hand, 1e-12,
          'DERIVED, TWO WAYS. The near plane at distance d has half-height '
          'd*tan(fov/2) in world units and H/2 in pixels, so a world length '
          'maps by their ratio. The second route projects two points and '
          'subtracts. Tolerance is 1e-12 because both are float64 evaluations '
          'of the same exact ratio -- anything larger would be hiding an '
          'algebra error behind round-off.', 'px')

    # Selection written as a distance and selection written as a pixel budget
    # are one statement. A renderer that computes one with tan(fov/2) and the
    # other with tan(fov) has two rules that agree nowhere and look right in
    # every screenshot taken at the distance they were tuned at.
    tau = 2.0
    ds = L.switch_distance(eps, H, FOV, tau)
    check(1, 'switch distance is the exact inverse of the error',
          L.screen_space_error(eps, H, FOV, ds), tau, 1e-12,
          'DERIVED. Round-tripping the closed form must return the budget it '
          'started from. This row is what catches a factor-of-two in the '
          'field-of-view halving, which is the single most common error in '
          'LOD selection and is invisible in a still frame.', 'px')

    # Error scales linearly in eps and inversely in distance. Stated as a ratio
    # so it cannot be satisfied by a constant that happens to fit one scene.
    check(1, 'error halves when distance doubles',
          L.screen_space_error(eps, H, FOV, 2.0 * d)
          / L.screen_space_error(eps, H, FOV, d),
          np.full(4, 0.5), 1e-12,
          'DERIVED. The projection is 1/d, so the ratio is exactly a half '
          'independent of eps, fov and resolution -- a dimensionless check '
          'that no tuning can make true by accident.', '-')

    # Distance to the NEAREST point of a node, not its centre.
    lo, hi = np.array([0.0, 0.0, 0.0]), np.array([100.0, 100.0, 10.0])
    cam = np.array([50.0, -5.0, 5.0])
    d_near = L.distance_to_aabb(cam, lo, hi)
    d_cent = float(np.linalg.norm(cam - 0.5 * (lo + hi)))
    check(1, 'distance-to-node is to its nearest point, not its centre',
          d_near, 5.0, 1e-12,
          'DERIVED. The camera sits 5 m outside one face and inside the other '
          'two extents, so the nearest point is the foot of that '
          'perpendicular and the distance is exactly 5. Measured to the '
          'centre it reads %.1f m -- a factor of %.1f, and it is worst for '
          'the largest nodes, which are exactly the ones a coarse level is '
          'made of.' % (d_cent, d_cent / d_near), 'm')
    info(1, 'centre-vs-nearest ratio on that node', round(d_cent / d_near, 2),
         'Reported rather than bounded: the ratio is unbounded as the camera '
         'approaches a large node\'s face, so there is no constant to assert. '
         'The row above pins the correct quantity instead.')


# ==========================================================================
#  B · THE MORPH AND THE CRACK CONTRACT
# ==========================================================================
def _sec_cracks():
    # The morph shortfall is an identity, and the reason morphK is not taste.
    for k, dh in ((0.98, 40.0), (0.90, 12.0), (1.00, 40.0)):
        pass
    check(1, 'an incomplete morph leaves exactly (1 - k) * delta_h',
          [L.morph_residual(40.0, 0.98), L.morph_residual(12.0, 0.90),
           L.morph_residual(40.0, 1.00)],
          [0.8, 1.2, 0.0], 1e-12,
          'DERIVED. If the blend reaches only k of the way to the parent '
          'position before the level switches, the vertex is still (1-k) of '
          'the way short, and that shortfall appears at the seam as a hole of '
          'exactly that height. morphK = 0.98 on a 40 m feature is 80 cm of '
          'daylight -- the number is small and the hole is not.', 'm')

    # The morph must reach 1 at the far edge of the band, or the switch is a pop.
    t_far = L.cdlod_morph(100.0, 50.0, 100.0)
    t_near = L.cdlod_morph(50.0, 50.0, 100.0)
    check(1, 'the morph completes across its band',
          [float(t_near), float(t_far)], [0.0, 1.0], 1e-12,
          'DERIVED. A morph that does not reach 1 by the switch distance is '
          'the previous row\'s defect written as a control-flow bug rather '
          'than a constant, and it produces the same hole.', '-')

    # The 2:1 balance condition, and the count when it is violated.
    check(1, 'the 2:1 restricted quadtree admits no T-junction',
          [L.t_junction_free(3, 3), L.t_junction_free(3, 4),
           L.t_junction_free(3, 5)],
          [True, True, False], 0,
          'DERIVED, COMBINATORIALLY. Two nodes sharing an edge tessellate it '
          'at 2**-level intervals; the finer one places 2**d - 1 vertices per '
          'coarse segment that the coarser edge does not contain, and each is '
          'a T-junction. d <= 1 is the case every stitching scheme is written '
          'for. d >= 2 is not a harder version of it -- it is a different '
          'problem, and a 2:1 stitcher leaks silently on it.', 'bool')
    check(1, 'extra edge vertices grow as 2**d - 1',
          [L.edge_vertex_mismatch(4, 3), L.edge_vertex_mismatch(5, 3),
           L.edge_vertex_mismatch(6, 3)], [1, 3, 7], 0,
          'DERIVED. The count a stitcher must handle, so "how bad is the '
          'violation" has a number rather than a shrug.', 'vertices')

    # A skirt is bounded below by the error it must hide.
    check(1, 'skirt depth is bounded below by the level\'s own world error',
          L.skirt_depth(0.8), 0.8, 1e-12,
          'DERIVED. A skirt occludes a crack rather than fixing one, so its '
          'depth is set by the largest vertical disagreement the boundary can '
          'show -- the level\'s own error -- and not by a constant tuned on '
          'one scene. A shorter skirt is a hole at the worst vertex.', 'm')


# ==========================================================================
#  C · GEOMETRY CLIPMAPS
# ==========================================================================
def _sec_clipmap():
    # The whole-texel invariant, fired both ways.
    ok = False
    try:
        L.clipmap_scroll(0, 1.5, 256)
    except ValueError:
        ok = True
    check(1, 'a fractional clipmap scroll is refused, not rounded',
          ok, True, 0,
          'DERIVED, AND THE GUARD IS FIRED RATHER THAN ASSUMED. A clipmap '
          'level is addressed modulo its size; scrolling it by a fraction of '
          'a texel resamples the whole level every frame and turns a '
          'band-limited pyramid into a swimming one. Rounding silently is the '
          'defect -- refusing is the contract.', 'bool')

    # The toroidal update covers exactly the newly exposed band, once.
    for o, n, size in ((0, 8, 256), (250, 8, 256), (128, -8, 256)):
        spans = L.clipmap_scroll(o, n, size)
        covered = sum(b - a for a, b in spans)
        check(1, 'toroidal refill covers |delta| texels exactly, at origin %d '
                 'delta %+d' % (o, n),
              covered, abs(n), 0,
              'DERIVED. The band a scroll exposes is |delta| texels wide '
              'however the window wraps; a refill that covers more is doing '
              'redundant work every frame, and one that covers less leaves a '
              'stale strip that reads as a seam travelling with the camera.',
              'texels')

    # Extent doubles per level -- the reason the pyramid is affordable.
    ext = [L.clipmap_level_extent(k, 255, 1.0) for k in range(4)]
    check(1, 'clipmap extent doubles per level',
          np.diff(np.log2(ext)), np.ones(3), 1e-12,
          'DERIVED. Constant texel count with doubling spacing gives a '
          'geometric footprint, which is what makes a fixed memory budget '
          'cover an exponentially growing world.', 'octaves')


# ==========================================================================
#  D · THE ISOSURFACE CASE ANALYSIS
# ==========================================================================
def _sec_tables():
    check(1, 'the cube symmetry group has 24 rotations and 48 with reflections',
          [len(T.cube_group(False)), len(T.cube_group(True))], [24, 48], 0,
          'DERIVED. Built by enumerating signed permutation matrices and '
          'keeping determinant +1, or +/-1. The group is the foundation every '
          'case count below stands on, so it is counted rather than quoted.',
          'elements')

    n_rc = len(T.case_orbits(reflections=False, complement=True))
    n_rrc = len(T.case_orbits(reflections=True, complement=True))
    n_r = len(T.case_orbits(reflections=False, complement=False))
    check(2, 'the classic "15 cases" is rotation + complement, WITHOUT '
             'reflection',
          n_rc, 15, 0,
          'PUBLISHED, AND THE ROW IS ABOUT WHICH FIFTEEN. Marching cubes is '
          'always introduced with fifteen base configurations, and every '
          'table is an expansion of them -- but the count depends on which '
          'symmetries are allowed, and an implementer copying a table whose '
          'author allowed a different set gets a subtly different expansion. '
          'Computed here: rotation+complement gives %d, rotation+reflection+'
          'complement gives %d, rotation alone gives %d. Only the first is '
          'the familiar number.' % (n_rc, n_rrc, n_r), 'classes')
    check(1, 'adding reflection merges the count to 14',
          n_rrc, 14, 0,
          'DERIVED. Two of the fifteen are mirror images of each other and '
          'nothing else, so allowing reflections fuses them. Stated because '
          '14, 15, 22 and 23 all appear in the literature for this same '
          'algorithm and the difference is entirely the group, not the '
          'geometry.', 'classes')

    amb = [m for m in range(256) if T.ambiguous_faces(m)]
    check(1, 'ambiguous faces are 120 of the 256 configurations',
          len(amb), 120, 0,
          'DERIVED, BY ENUMERATION. A face whose two diagonal corners are '
          'inside and the other two outside admits two topologies and the '
          'cube alone does not choose. This is not a corner case: it is '
          '%.0f%% of the table, which is why "marching cubes sometimes leaves '
          'holes" is a near-certainty on real data rather than bad luck.'
          % (100.0 * len(amb) / 256.0), 'configurations')

    # The decider is a FUNCTION OF THE SHARED FACE ONLY, which is the whole
    # reason it closes the hole.
    fa, fb, fc, fd = 1.0, -1.0, 1.0, -1.0
    same = T.asymptotic_decider(fa, fb, fc, fd)
    swapped = T.asymptotic_decider(fc, fd, fa, fb)
    check(1, 'the asymptotic decider is invariant under the face\'s own '
             'half-turn',
          [same, swapped], [same, same], 0,
          'DERIVED. Two cubes sharing a face enumerate its corners starting '
          'from different places; if the decider depended on where the cycle '
          'started, the two would disagree and the gap it exists to close '
          'would reopen. A half-turn maps (a,b,c,d) to (c,d,a,b) and the '
          'saddle expression is symmetric under it.', 'bool')
    check(1, 'signs alone cannot resolve an ambiguous face',
          T.face_contour_from_corners_only(0b01011010, T.FACES[0]) is None
          or not T.face_is_ambiguous(0b01011010, T.FACES[0]),
          True, 0,
          'DERIVED. The counterpart to the decider and the reason it is '
          'needed: on an ambiguous face the sign-only rule has no answer, so '
          'any implementation that returns one has invented it -- and two '
          'neighbours inventing independently disagree half the time.', 'bool')

    # Edge interpolation places a shared vertex identically from both sides.
    t_ab = T.edge_interp(-2.0, 6.0)
    t_ba = T.edge_interp(6.0, -2.0)
    check(1, 'an edge crossing lands in the same place from either end',
          t_ab, 1.0 - t_ba, 1e-15,
          'DERIVED. t = (iso - v0)/(v1 - v0) read from the far end gives '
          '1 - t, i.e. the same world position. This is what welds two cubes '
          'triangles into one surface; dividing by either value instead of '
          'their difference breaks it and leaves a visible crack along every '
          'shared edge.', '-')

    a, b = T.transition_face_samples(2)
    check(2, 'a Transvoxel transition face sees 4 samples against 9',
          [a, b], [4, 9], 0,
          'PUBLISHED STRUCTURE. The half-resolution side samples the shared '
          'face on n x n, the full-resolution side on (2n-1) x (2n-1). The '
          'five extra samples are the entire difficulty: the coarse side '
          'cannot see them, so the transition cell must agree with the coarse '
          'side\'s straight edges while still using the fine side\'s data.',
          'samples')


# ==========================================================================
#  E · RESIDENCY, STREAMING AND THE HiZ FOOTPRINT
# ==========================================================================
def _sec_budget():
    # The series against the sum -- the row that would have caught chapter 06's
    # arithmetic before a reader did.
    n = 8
    check(1, 'the pyramid total matches its closed-form series',
          B.pyramid_tiles(n), sum(B.tiles_at_level(k) for k in range(n)), 0,
          'DERIVED. sum(4**k, k<n) = (4**n - 1)/3, computed both ways. A '
          'worked example nobody re-adds is a decoration: this skill shipped '
          'a residency table whose ring column was off by about fifty tiles '
          'until somebody added it up.', 'tiles')

    ring = B.ring_tiles(8, 5)
    whole = B.pyramid_tiles(8)
    between(1, 'ring residency is far below the whole pyramid',
            float(whole) / float(ring), 100.0, 1000.0,
            'DERIVED. A fixed window per level is a linear cost against the '
            'pyramid\'s geometric one, so the ratio GROWS with depth rather '
            'than being a constant factor -- which is the argument for '
            'clipmap-shaped residency and is why it is stated as a formula '
            'and not as one scene\'s number. At 8 levels and a 5x5 ring it '
            'is %.0fx.' % (whole / ring), 'x')

    base = B.tile_bytes(256, 4, 1, False)
    # THE TOLERANCE COMES FROM THE ESTIMATOR, and this row is where that rule
    # earned its place: at 1e-6 it failed, because `tile_bytes` rounds to whole
    # bytes and the ratio therefore CANNOT reach 4/3 exactly. The rounding is
    # at most half a byte, so the ratio's error is at most 0.5/base -- which is
    # the number below. Widening until green would have hidden the fact that
    # the quantity is an integer; deriving the bound says so out loud.
    tol = 0.5 / base
    check(1, 'a mip chain adds exactly one third, to the byte',
          B.tile_bytes(256, 4, 1, True) / base, 4.0 / 3.0, tol,
          'DERIVED. sum(4**-k) = 4/3, so the chain is a third of the base and '
          'not a rounding error -- it is the term most often dropped from a '
          'budget, because the tile size is what a person remembers and the '
          'chain is what the allocator sees. Tolerance %.2e is half a byte '
          'over the %d-byte base, which is the whole error a byte-rounded '
          'ratio can carry; anything looser would be hiding an algebra '
          'mistake behind an integer.' % (tol, base), '-')

    # The HiZ rule, tested as the property it is chosen to guarantee.
    ok, bad = [], []
    for w in (1, 2, 3, 5, 8, 9, 17, 31, 64):
        m = B.hiz_mip_for_rect(w, w)
        ok.append(B.hiz_rect_spans_2x2(w, w, m))
        bad.append(B.hiz_rect_spans_2x2(w, w, max(m - 1, 0)) if w > 1 else True)
    check(1, 'ceil(log2 extent) makes a 2x2 fetch span the rect at every offset',
          ok, [True] * len(ok), 0,
          'DERIVED. At mip m a texel covers 2**m of mip 0, so a rect of '
          'extent w occupies at most ceil(w / 2**m) texels; m = '
          'ceil(log2 w) makes that one, and a one-texel extent lies inside '
          'some 2x2 block at any alignment.', 'bool')
    check(1, 'one mip coarser is NOT enough, so the rule is tight',
          sum(1 for v in bad if not v) > 0, True, 0,
          'RULING 14 WITH THE SIGN FLIPPED: a guard never seen to fail is not '
          'known to be a guard. Dropping one mip leaves the rect up to two '
          'texels wide, which straddles a 2x2 block for some offsets and '
          'returns a depth that is not conservative -- an occlusion test that '
          'occasionally culls something visible. %d of the %d widths tried '
          'fail at m-1, so the ceiling is doing work.'
          % (sum(1 for v in bad if not v), len(bad)), 'bool')

    # Latency is per-request unless requests overlap.
    t_amort = B.stream_time(100e6, 2e9, 0.0)
    t_real = B.stream_time(100e6, 2e9, 0.004)
    check(1, 'a fixed latency is not amortised by bandwidth',
          t_real - t_amort, 0.004, 1e-12,
          'DERIVED, AND IT IS AN ADDITION RATHER THAN A DIVISION. A budget '
          'that divides total bytes by total bandwidth has assumed the '
          'latency away; on a request-per-tile pipeline it is paid per tile '
          'unless the requests are in flight together, which is what the '
          'priority queue and the no-holes rule exist to arrange.', 's')

    # Morton: the inverse is the only honest test of the forward map.
    pts = [(x, y) for x in range(16) for y in range(16)]
    rt = [B.morton2_inverse(B.morton2(x, y)) for x, y in pts]
    check(1, 'Morton interleave round-trips for every cell',
          rt == pts, True, 0,
          'DERIVED. A forward map checked against a hand-picked value passes '
          'with the bits swapped; round-tripping the whole grid does not.',
          'bool')
    m_loc = B.order_locality(lambda x, y: B.morton2(x, y), 32)
    r_loc = B.order_locality(lambda x, y: y * 32 + x, 32)
    check(3, 'Z-order is measurably more local than row-major',
          m_loc < r_loc, True, 0,
          'INDEPENDENT METHOD, AND MEASURED RATHER THAN ASSERTED. Mean '
          'world-space step between tiles consecutive in the ordering: '
          '%.3f for Morton against %.3f for row-major. "Morton is local" is '
          'true in a sense a wrong implementation also satisfies, so the row '
          'compares a number.' % (m_loc, r_loc), '-')


# ==========================================================================
#  the deliberate defects
# ==========================================================================
def _bug_sse_full_fov(mod):
    """The field of view not halved -- the classic factor-of-two."""
    orig = mod.pixels_per_world_unit

    def bad(screen_h, fov_y_rad, dist):
        return orig(screen_h, 2.0 * fov_y_rad, dist)
    mod.pixels_per_world_unit = bad


def _bug_lod_centre_distance(mod):
    """Node distance measured to the centre instead of the nearest point."""
    def bad(p, lo, hi):
        p, lo, hi = np.asarray(p, float), np.asarray(lo, float), np.asarray(hi, float)
        return float(np.linalg.norm(p - 0.5 * (lo + hi)))
    mod.distance_to_aabb = bad


def _bug_hiz_floor(mod):
    """floor instead of ceil in the HiZ mip rule."""
    def bad(w, h):
        n = max(int(w), int(h), 1)
        return int(math.floor(math.log2(n))) if n > 1 else 0
    mod.hiz_mip_for_rect = bad


def _bug_clipmap_rounds(mod):
    """A fractional scroll silently rounded rather than refused."""
    orig = mod.clipmap_scroll

    def bad(origin, delta, size):
        return orig(origin, int(round(delta)), size)
    mod.clipmap_scroll = bad


def _bug_edge_interp_divides_by_v1(mod):
    """The edge crossing divided by an endpoint instead of the difference."""
    def bad(v0, v1, iso=0.0):
        return 0.5 if abs(v1) < 1e-300 else (float(iso) - float(v0)) / float(v1)
    mod.edge_interp = bad


def _bug_mip_chain_ignored(mod):
    """The mip chain dropped from the tile budget."""
    orig = mod.tile_bytes

    def bad(texels, channels=4, bytes_per_channel=1, mip_chain=True):
        return orig(texels, channels, bytes_per_channel, False)
    mod.tile_bytes = bad


BUGS.update({
    'sse-full-fov': (_bug_sse_full_fov, 'lod'),
    'lod-centre-distance': (_bug_lod_centre_distance, 'lod'),
    'hiz-floor': (_bug_hiz_floor, 'budget'),
    'clipmap-rounds': (_bug_clipmap_rounds, 'lod'),
    'edge-interp-by-v1': (_bug_edge_interp_divides_by_v1, 'tables'),
    'mip-chain-ignored': (_bug_mip_chain_ignored, 'budget'),
})

SECTIONS = ((_sec_sse, 'screen-space error, the currency'),
            (_sec_cracks, 'the morph and the crack contract'),
            (_sec_clipmap, 'geometry clipmaps and the toroidal update'),
            (_sec_tables, 'the isosurface case analysis'),
            (_sec_budget, 'residency, streaming and the HiZ footprint'))


def run_suite():
    del ROWS[:]
    for fn, label in SECTIONS:
        try:
            fn()
        except Exception as exc:                                # noqa: BLE001
            ROWS.append(Row(0, 'section "%s" raised' % label, '-',
                            '%s: %s' % (type(exc).__name__, exc), '-',
                            'ERROR', 'A section that crashes takes its rows '
                            'with it; the guard records the crash as a row so '
                            'a lost section cannot look like a clean run.', ''))


def report(verbose=False, title=''):
    n_pass = sum(r.status == 'PASS' for r in ROWS)
    n_fail = sum(r.status == 'FAIL' for r in ROWS)
    n_info = sum(r.status == 'INFO' for r in ROWS)
    n_err = sum(r.status == 'ERROR' for r in ROWS)
    print('=' * 96)
    if title:
        print(title)
    print('%-4s %-56s %14s %14s %7s' % ('tier', 'row', 'expected', 'measured',
                                        'status'))
    print('-' * 96)
    for r in ROWS:
        print('%-4s %-56s %14s %14s %7s'
              % (r.tier, r.name[:56], _fmt(r.exp) if r.exp is not None else '-',
                 _fmt(r.got), r.status))
        if verbose or r.status in ('FAIL', 'ERROR'):
            for line in _wrap(r.why, 88):
                print('       ' + line)
    print('=' * 96)
    print('%d pass, %d FAIL, %d info, %d ERROR' % (n_pass, n_fail, n_info, n_err))
    print('=' * 96)
    return n_fail + n_err


def _wrap(s, w):
    out, cur = [], ''
    for word in str(s).split():
        if len(cur) + len(word) + 1 > w:
            out.append(cur)
            cur = word
        else:
            cur = (cur + ' ' + word).strip()
    if cur:
        out.append(cur)
    return out


def run_bugs():
    """Re-run the whole suite once per deliberately reintroduced defect.

    A SUITE THAT CATCHES NOTHING IS THE FAILURE THIS GUARDS AGAINST. Each entry
    below breaks one thing at roughly the size of a real regression; the run
    fails if any of them slips through every row.
    """
    import importlib
    mods = {'lod': L, 'budget': B, 'tables': T}
    print('%-24s %-8s %s' % ('defect', 'caught', 'rows that fired'))
    print('-' * 96)
    missed = []
    for name, (apply_fn, modname) in sorted(BUGS.items()):
        for m in mods.values():
            importlib.reload(m)
        apply_fn(mods[modname])
        run_suite()
        fired = [r.name for r in ROWS if r.status in ('FAIL', 'ERROR')]
        print('%-24s %-8s %s' % (name, 'yes' if fired else 'NO',
                                 '; '.join(f[:44] for f in fired[:3])
                                 or '** nothing fired **'))
        if not fired:
            missed.append(name)
    for m in mods.values():
        importlib.reload(m)
    print('-' * 96)
    print('%d of %d defects caught' % (len(BUGS) - len(missed), len(BUGS)))
    return len(missed)


if __name__ == '__main__':
    if '--bugs' in sys.argv:
        raise SystemExit(run_bugs())
    run_suite()
    raise SystemExit(report('-v' in sys.argv,
                            'validate_terrain.py -- external checks on this '
                            'skill\'s own arithmetic'))
