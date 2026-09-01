"""Screen-space error, the LOD controllers built on it, and the crack contract.

WHY THIS FILE EXISTS. `SKILL.md` says screen-space error is "the universal
currency" and that "cracks are prevented by contract, never healed". Both are
statements about arithmetic, and until this file existed nothing checked either
of them. Chapter `11` prescribes verification for the reader's renderer while
the chapters prescribing it had none of their own -- which is the ninth way a
verification fails, applied to a whole skill.

WHAT IS DERIVED HERE AND WHAT IS QUOTED. The projection algebra, the morph
shortfall, the T-junction condition and the clipmap scroll invariant are
DERIVED -- they follow from a perspective divide and from integer arithmetic,
and a disagreement is a bug in one of the two. The technique NAMES (geometry
clipmaps, CDLOD, ROAM, chunked LOD) and their attributions belong to
`references/00-index.md` and are not restated here; this file contains no
citations because it contains no claims that need one.

NOTHING HERE IS A RENDERER. There is no GPU, no mesh, no draw call. Every
function answers a question of the form "does this arithmetic say what the
chapter says it says", which is the only kind of question a file without a
graphics device can honestly answer -- and it is the kind where being wrong is
silent, because a screen-space error that is off by a factor of two still
produces a picture.
"""
import math

import numpy as np


# ---------------------------------------------------------------- the currency
def pixels_per_world_unit(screen_h, fov_y_rad, dist):
    """How many pixels one world unit subtends at `dist`, on the view axis.

    THE WHOLE OF LOD SELECTION IS THIS NUMBER. A perspective camera maps a
    world-space length `L` at distance `d`, perpendicular to the view axis, to

        pixels = L * (H/2) / (d * tan(fov_y/2))

    because the near plane's half-height in world units at distance `d` is
    `d*tan(fov_y/2)` and it covers `H/2` pixels. Everything below is this
    identity rearranged, which is why the suite checks the rearrangements
    against it rather than against each other.
    """
    d = np.maximum(np.asarray(dist, float), 1e-12)
    return 0.5 * float(screen_h) / (d * math.tan(0.5 * float(fov_y_rad)))


def screen_space_error(eps_world, screen_h, fov_y_rad, dist):
    """The geometric error of a LOD, in pixels, at a viewing distance.

    `eps_world` is the maximum world-space deviation between this level's
    surface and the finest one -- for a heightfield, the largest vertical
    displacement removed by the decimation. It is a property of the DATA and
    the LOD, computed once at build time, never at runtime.
    """
    return np.asarray(eps_world, float) * pixels_per_world_unit(
        screen_h, fov_y_rad, dist)


def switch_distance(eps_world, screen_h, fov_y_rad, tau_px):
    """The distance at which a level's error first falls under the budget.

    The exact inverse of `screen_space_error`, and it must be, because a
    selection rule written as a distance and an error budget written in pixels
    are the same statement seen from two ends. A renderer that computes one
    with `tan(fov/2)` and the other with `tan(fov)` has two rules that agree
    nowhere and look plausible everywhere.
    """
    tau = np.maximum(np.asarray(tau_px, float), 1e-12)
    return (np.asarray(eps_world, float) * 0.5 * float(screen_h)
            / (tau * math.tan(0.5 * float(fov_y_rad))))


def distance_to_aabb(p, lo, hi):
    """Distance from a point to the NEAREST point of an axis-aligned box.

    ⚠️ AND NOT TO ITS CENTRE, WHICH IS THE BUG THIS FUNCTION EXISTS TO NAME.
    Selecting LOD on distance-to-centre makes a node's error depend on its own
    size: a large node whose near face is at the camera is scored as though it
    were half a diagonal further away, so the coarsest levels are exactly the
    ones the rule mis-scores worst. The ratio `d_centre/d_nearest` is unbounded
    as the camera approaches a face.
    """
    p = np.asarray(p, float)
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    d = np.maximum(np.maximum(lo - p, p - hi), 0.0)
    return float(np.sqrt(np.sum(d * d, axis=-1))) if d.ndim == 1 else np.sqrt(
        np.sum(d * d, axis=-1))


# ------------------------------------------------------------------- the morph
def cdlod_morph(dist, d_near, d_far, morph_start=0.0):
    """The morph parameter `t` in [0, 1] across a level's transition band.

    CDLOD blends a level's vertices toward its parent's over the outer part of
    its distance range, so a vertex that is about to be dropped has already
    reached the position it will have after the drop. `t = 0` is "fully this
    level", `t = 1` is "geometrically identical to the parent".
    """
    d = np.asarray(dist, float)
    lo = d_near + float(morph_start) * (d_far - d_near)
    return np.clip((d - lo) / max(d_far - lo, 1e-12), 0.0, 1.0)


def morph_residual(delta_h, morph_k):
    """The vertical crack a morph that does not COMPLETE leaves behind.

    An identity, and the reason `morphK` is not a taste parameter: if the blend
    reaches only `morph_k` of the way to the parent before the switch, the
    vertex is still `(1 - morph_k) * delta_h` away from where the parent puts
    it, and that difference appears at the seam as a crack of exactly that
    height. `morph_k = 0.98` on a 40 m feature is an 80 cm hole.
    """
    return (1.0 - np.asarray(morph_k, float)) * np.asarray(delta_h, float)


# ----------------------------------------------------------- the crack contract
def t_junction_free(level_a, level_b, restricted=True):
    """Can two adjacent quadtree nodes meet without a T-junction?

    THE CONTRACT, STATED AS A PREDICATE. Two nodes sharing an edge tessellate
    it at 2**-level intervals. The finer node puts vertices on the shared edge
    that the coarser node's edge does not contain, and each such vertex is a
    T-junction: it lies on the coarser triangle's edge but is not one of its
    corners, so any displacement at that vertex opens a hole.

    With a RESTRICTED quadtree -- neighbours differ by at most one level, the
    2:1 balance condition -- the finer edge has exactly one extra vertex per
    coarse edge, which is the case every stitching scheme is written for. Two
    or more levels of difference is not a harder case of the same problem; it
    is a different one, and a stitcher written for 2:1 will silently leak.
    """
    d = abs(int(level_a) - int(level_b))
    return d <= (1 if restricted else 0)


def edge_vertex_mismatch(level_fine, level_coarse):
    """How many vertices the finer edge carries that the coarser one does not.

    `2**d - 1` per coarse edge segment, so the 2:1 case is one, and the count
    grows as fast as the level difference does. A number rather than a boolean,
    because "how bad is it" is what a reviewer asks after "is it wrong".
    """
    d = max(int(level_fine) - int(level_coarse), 0)
    return (1 << d) - 1


def skirt_depth(eps_world, safety=1.0):
    """How far a skirt must hang to hide the worst crack it can be asked to.

    A skirt is a band of geometry dropped vertically at a patch boundary; it
    does not FIX a crack, it occludes one. So its depth is bounded below by the
    largest vertical disagreement the boundary can show, which is the level's
    own world-space error -- not by a constant chosen to look right on one
    scene. `safety` is a multiplier, and 1.0 means "exactly enough at the worst
    vertex", which is the number to justify a departure from.
    """
    return float(safety) * np.asarray(eps_world, float)


# --------------------------------------------------------- geometry clipmaps
def clipmap_scroll(origin_texels, delta_texels, size):
    """Toroidal update: which texel range the ring buffer must refill.

    THE INVARIANT IS THAT THE SCROLL IS AN INTEGER NUMBER OF TEXELS. A clipmap
    level is a window on a grid, addressed modulo its size; moving it by a
    fractional texel would resample the whole level every frame and turn a
    band-limited pyramid into a swimming one. The chapter states this as a
    contract; here it is arithmetic, and the function refuses a fractional
    argument rather than rounding it silently.
    """
    if int(delta_texels) != delta_texels:
        raise ValueError('clipmap scroll must be a whole number of texels, '
                         'got %r -- a fractional scroll resamples the level '
                         'every frame' % (delta_texels,))
    o = int(origin_texels) % int(size)
    n = int(delta_texels)
    if n == 0:
        return []
    if abs(n) >= int(size):
        return [(0, int(size))]
    start = (o + int(size)) % int(size) if n > 0 else (o + n) % int(size)
    width = abs(n)
    end = start + width
    if end <= int(size):
        return [(start, end)]
    return [(start, int(size)), (0, end - int(size))]


def clipmap_level_extent(level, texels, finest_spacing):
    """The world-space side length a clipmap level covers.

    Each coarser level doubles its spacing while keeping its texel count, so
    extent doubles per level and the pyramid's total footprint is a geometric
    series -- which is the whole reason the structure is affordable and the
    number a memory budget is read off.
    """
    return float(texels) * float(finest_spacing) * (2.0 ** int(level))
