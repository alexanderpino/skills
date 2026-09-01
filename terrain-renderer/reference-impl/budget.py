"""Tile-pyramid arithmetic, residency, and the HiZ footprint rule.

WHY THIS FILE EXISTS. Two of this skill's numeric claims were reached by hand
and never re-run. Chapter `06`'s streaming worked example is a table of tile
counts and megabytes; chapter `08`'s HiZ rule is a mip-selection argument whose
whole content is a `ceil(log2 ...)`. Both are arithmetic, both are the kind of
arithmetic that is wrong by a factor of two without looking wrong, and one of
them WAS wrong -- the ring column of `06`'s table summed to about 205 tiles
where the text said 255, found by adding it up rather than by reading it.

A worked example nobody re-adds is a decoration. This file makes them
re-addable.
"""
import math

import numpy as np


# ------------------------------------------------------------- the tile pyramid
def tiles_at_level(level, root_tiles=1):
    """Tiles on one level of a quadtree pyramid: `root * 4**level`."""
    return int(root_tiles) * (4 ** int(level))


def pyramid_tiles(n_levels, root_tiles=1):
    """Every tile in a full pyramid -- the geometric series, in closed form.

    `root * (4**n - 1)/3`. Written closed-form rather than summed because the
    point of the row that checks it is to catch a sum that disagrees with the
    series, and two loops that agree prove nothing.
    """
    n = int(n_levels)
    return int(root_tiles) * (4 ** n - 1) // 3


def ring_tiles(n_levels, ring, root_tiles=1):
    """Tiles resident under a RING policy: a fixed window per level.

    The alternative to holding a whole pyramid: keep only a `ring x ring`
    neighbourhood at each level, centred on the viewer. The saving is the whole
    argument for clipmap-shaped residency, and it is a difference between a
    geometric series and a linear one -- so it grows with depth rather than
    being a constant factor, which is why it is worth stating as a formula and
    not as one scene's number.
    """
    per = min(int(ring) ** 2, int(root_tiles) * 4 ** 0)
    del per
    out = 0
    for lv in range(int(n_levels)):
        out += min(int(ring) ** 2, tiles_at_level(lv, root_tiles))
    return out


def tile_bytes(texels, channels=4, bytes_per_channel=1, mip_chain=True):
    """Memory for one tile, with or without its own mip chain.

    A mip chain adds exactly 1/3 in the limit -- `sum 4**-k = 4/3` -- and that
    third is the term most often dropped from a budget, because the tile size
    is what a person remembers and the chain is what the hardware allocates.
    """
    base = int(texels) * int(texels) * int(channels) * int(bytes_per_channel)
    return int(round(base * (4.0 / 3.0))) if mip_chain else base


def residency_bytes(n_levels, ring, texels, channels=4, bytes_per_channel=1,
                    mip_chain=True, root_tiles=1):
    """The whole budget line, from the policy and the format."""
    return ring_tiles(n_levels, ring, root_tiles) * tile_bytes(
        texels, channels, bytes_per_channel, mip_chain)


# --------------------------------------------------------- the streaming clock
def stream_time(bytes_needed, bandwidth_bytes_per_s, latency_s=0.0):
    """How long a residency change takes: transfer plus a fixed latency.

    ⚠️ THE LATENCY IS NOT AMORTISED BY BANDWIDTH, and a budget that divides
    total bytes by total bandwidth has assumed it is. On a request-per-tile
    pipeline the latency is paid PER TILE unless the requests are in flight
    together, which is exactly what the no-holes rule and the priority queue
    exist to arrange.
    """
    return (float(bytes_needed) / max(float(bandwidth_bytes_per_s), 1e-12)
            + float(latency_s))


def prefetch_radius(speed_m_per_s, stream_s, tile_m, safety=1.5):
    """How far ahead residency must reach for a mover at a given speed.

    A ring sized for the standing case tears the moment the camera moves: the
    viewer crosses `speed * stream_s` metres while a tile loads, so the ring
    has to lead by at least that, in tiles, times a margin for the worst
    heading. This is the number a "hitches when flying" bug is measured
    against, and it is usually absent rather than wrong.
    """
    return float(safety) * float(speed_m_per_s) * float(stream_s) / max(
        float(tile_m), 1e-12)


# ------------------------------------------------------------------ HiZ / occlusion
def hiz_mip_for_rect(w_texels, h_texels):
    """The mip whose texels are coarse enough that a 2x2 fetch spans the rect.

    THE RULE, AND WHY IT IS `ceil` AND NOT `floor`. A screen-space bounding
    rectangle `w x h` texels is tested against a hierarchical depth pyramid by
    reading a single 2x2 neighbourhood. At mip `m` a texel covers `2**m`
    texels of mip 0, so the rect spans at most `ceil(w / 2**m)` of them; taking
    `m = ceil(log2(max(w, h)))` makes that at most 1, and a rect of extent at
    most one texel is always contained in some 2x2 block whatever its
    alignment. `floor` leaves the rect up to two texels wide, which straddles a
    2x2 block for some offsets and reads a depth that is not conservative --
    an occlusion test that occasionally culls something visible, which is the
    hardest class of bug in this chapter to see.
    """
    n = max(int(w_texels), int(h_texels), 1)
    return int(math.ceil(math.log2(n))) if n > 1 else 0


def hiz_rect_spans_2x2(w_texels, h_texels, mip):
    """Does a 2x2 fetch at `mip` cover the rect at EVERY sub-texel offset?

    The property the rule above is chosen to guarantee, tested directly rather
    than argued: a rect of width `w` at offset `o` occupies texels
    `floor(o / s)` through `floor((o + w) / s)` where `s = 2**mip`, so it fits
    in two texels for all `o` exactly when `w <= s`.
    """
    s = float(2 ** int(mip))
    return float(w_texels) <= s and float(h_texels) <= s


# ------------------------------------------------------------ spatial ordering
def morton2(x, y, bits=16):
    """Interleave two integers -- the Z-order curve.

    Tile ordering decides how much of a streaming request is one contiguous
    read. Morton is the cheap answer and its locality is what a tile server's
    hit rate is built on; the row that checks it measures locality rather than
    asserting it, because "Morton is local" is true in a sense that a wrong
    implementation also satisfies.
    """
    def part(v):
        v &= (1 << bits) - 1
        out = 0
        for i in range(bits):
            out |= (v & (1 << i)) << i
        return out
    return part(int(x)) | (part(int(y)) << 1)


def morton2_inverse(code, bits=16):
    """The exact inverse, which is the only honest test of the forward map."""
    x = y = 0
    for i in range(bits):
        x |= ((int(code) >> (2 * i)) & 1) << i
        y |= ((int(code) >> (2 * i + 1)) & 1) << i
    return x, y


def order_locality(order_fn, n=32):
    """Mean world-space step between consecutive tiles under an ordering.

    A single number that separates row-major from Z-order without appealing to
    a picture: enumerate an `n x n` grid in the order's own sequence and average
    the Euclidean distance between neighbours in that sequence. Row-major pays
    a full row width once per row; Morton does not.
    """
    pts = sorted(((order_fn(x, y), x, y) for x in range(n) for y in range(n)))
    p = np.array([[x, y] for _, x, y in pts], float)
    d = np.linalg.norm(np.diff(p, axis=0), axis=1)
    return float(d.mean())
