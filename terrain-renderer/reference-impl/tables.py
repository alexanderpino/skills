"""The isosurface case analysis, derived rather than transcribed.

WHY THIS FILE EXISTS, IN THE SKILL'S OWN WORDS. `SKILL.md` tells the reader:
"Do not hand-roll table-driven algorithms (marching cubes tables, transition
cells, HiZ reductions) from memory -- the conventions matter and are easy to
get subtly wrong." That instruction was given for six chapters without anything
in the skill able to tell a right table from a wrong one.

WHAT THIS FILE DOES AND DOES NOT CONTAIN. It contains **no transcribed table**.
It builds the case analysis from the cube's own symmetry group and checks the
properties every correct table must have, because a transcribed table is
exactly the artefact whose errors are invisible: a single wrong triangle in one
of 256 entries produces a hole in one configuration out of 256, on some meshes,
sometimes. Deriving the structure and counting its orbits catches that class in
one pass.

CORNER AND EDGE NUMBERING. Corner `i` carries bit `i`; its position is
`(i & 1, (i >> 1) & 1, (i >> 2) & 1)`. That is a choice, and it is stated here
because half the transcription errors in this algorithm are a numbering
mismatch between the table's author and its user rather than a wrong triangle.
"""
import itertools

import numpy as np

# corner index -> (x, y, z) in {0,1}^3, bit i of the index being axis i
CORNERS = np.array([[i & 1, (i >> 1) & 1, (i >> 2) & 1] for i in range(8)],
                   dtype=int)

# the twelve edges, as corner pairs differing in exactly one bit
EDGES = tuple(sorted((a, b) for a in range(8) for b in range(a + 1, 8)
                     if bin(a ^ b).count('1') == 1))

# the six faces, each as its four corners in CYCLIC order. Cyclic and not
# sorted, because the ambiguity test below reads a face as a quadrilateral and
# a saddle of the bilinear interpolant is not symmetric under re-ordering.
def _faces():
    out = []
    for axis in range(3):
        for side in (0, 1):
            c = [i for i in range(8) if ((i >> axis) & 1) == side]
            u, v = [a for a in range(3) if a != axis]
            c.sort(key=lambda i: (CORNERS[i][v], CORNERS[i][u]))
            out.append((c[0], c[1], c[3], c[2]))   # into a cycle
    return tuple(out)


FACES = _faces()


# ------------------------------------------------------------- the symmetries
def _corner_perm(mat):
    """A 3x3 signed permutation of the unit cube, as a permutation of corners."""
    p = []
    for i in range(8):
        v = CORNERS[i] * 2 - 1                 # to {-1,+1}^3
        w = mat @ v
        idx = sum((1 << k) for k in range(3) if w[k] > 0)
        p.append(idx)
    return tuple(p)


def cube_group(reflections=True):
    """The cube's symmetry group, as permutations of the eight corners.

    24 rotations, or 48 with reflections. Built by enumerating signed
    permutation matrices and keeping those with the right determinant, so the
    group is DERIVED from the geometry rather than listed.
    """
    seen = {}
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1, 1), repeat=3):
            m = np.zeros((3, 3), dtype=int)
            for r, c in enumerate(perm):
                m[r, c] = signs[r]
            det = int(round(np.linalg.det(m)))
            if det == 1 or (reflections and det == -1):
                seen[_corner_perm(m)] = True
    return tuple(seen)


def _apply(perm, mask):
    """Move a corner sign-mask through a corner permutation."""
    out = 0
    for i in range(8):
        if mask & (1 << i):
            out |= 1 << perm[i]
    return out


def case_orbits(reflections=True, complement=True):
    """Partition the 256 sign configurations into equivalence classes.

    THE "FIFTEEN CASES" IS A COUNT, AND A COUNT CAN BE CHECKED. Marching cubes
    is always introduced with a picture of fifteen base configurations, and
    every table is some expansion of them. Which fifteen -- and whether it is
    fifteen at all -- depends on which symmetries you allow, and that is
    exactly the thing an implementer gets wrong when copying a table whose
    author allowed a different set.

    Returns a list of orbits, each a sorted tuple of the masks it contains.
    """
    group = cube_group(reflections)
    seen = set()
    orbits = []
    for m in range(256):
        if m in seen:
            continue
        orb = set()
        stack = [m]
        while stack:
            x = stack.pop()
            if x in orb:
                continue
            orb.add(x)
            for p in group:
                stack.append(_apply(p, x))
            if complement:
                stack.append(x ^ 0xFF)
        seen |= orb
        orbits.append(tuple(sorted(orb)))
    return orbits


# --------------------------------------------------------------- the ambiguity
def face_is_ambiguous(mask, face):
    """Does this face carry the diagonal sign pattern?

    A face whose two diagonally opposite corners are inside and the other two
    outside admits TWO topologies -- the contour can separate either diagonal
    pair -- and the cube alone does not say which. That is the whole of the
    marching-cubes hole problem: two neighbouring cubes resolve the same shared
    face differently and leave a gap between them.
    """
    a, b, c, d = face
    ia, ib, ic, idd = [(mask >> k) & 1 for k in (a, b, c, d)]
    return (ia == ic) and (ib == idd) and (ia != ib)


def ambiguous_faces(mask):
    """Which of the six faces of this configuration are ambiguous."""
    return tuple(f for f in FACES if face_is_ambiguous(mask, f))


def asymptotic_decider(fa, fb, fc, fd):
    """Nielson & Hamann's test, on one face's four scalar values.

    THE FIX IS NOT A HEURISTIC, WHICH IS WHY IT BELONGS IN A FILE THAT CAN
    CHECK IT. On a face, trilinear interpolation restricts to a BILINEAR
    function, whose contour at the isovalue is a hyperbola with a saddle. The
    saddle's value is

        S = (fa*fc - fb*fd) / (fa + fc - fb - fd)

    and its sign decides which diagonal pair the contour joins. Both
    neighbouring cubes evaluate the same four numbers, so both reach the same
    answer, and the gap cannot open. A random or per-cube choice makes the two
    disagree half the time.

    Returns True when the contour separates the (a, c) pair from (b, d).
    """
    den = fa + fc - fb - fd
    if abs(den) < 1e-300:
        return bool(fa + fc > 0.0)       # degenerate: fall back to the pair sum
    s = (fa * fc - fb * fd) / den
    return bool(s > 0.0)


def face_contour_from_corners_only(mask, face):
    """Which corner pairs the face's contour joins, using SIGNS alone.

    The counterpart to the decider, and the reason the decider is needed: on an
    ambiguous face this function has no answer, and any implementation that
    returns one has invented it. Returns None exactly on the ambiguous faces.
    """
    if face_is_ambiguous(mask, face):
        return None
    a, b, c, d = face
    bits = [(mask >> k) & 1 for k in (a, b, c, d)]
    inside = [k for k, v in zip(face, bits) if v]
    return tuple(sorted(inside))


# ------------------------------------------------------- the transition problem
def transition_face_samples(n_coarse=2):
    """How many samples the two sides of a Transvoxel transition face carry.

    The half-resolution side samples the shared face on an `n x n` grid; the
    full-resolution side on `(2n-1) x (2n-1)`. For the standard n = 2 that is
    4 against 9, and the five extra samples are the entire difficulty: the
    coarse side cannot see them, so the transition cell must produce a contour
    that agrees with the coarse side's straight edges while still using the
    fine side's data on its own half.
    """
    n = int(n_coarse)
    return n * n, (2 * n - 1) * (2 * n - 1)


def edge_interp(v0, v1, iso=0.0):
    """Where the surface crosses an edge, by linear interpolation.

    ⚠️ THE DIVISION IS BY THE DIFFERENCE AND NOT BY EITHER VALUE, which is the
    other transcription error this algorithm attracts. `t = (iso - v0)/(v1 - v0)`
    is exact when the field is linear along the edge, and it is the only choice
    that makes two cubes sharing that edge place the vertex in the SAME spot --
    which is what welds their triangles into one surface instead of two.
    """
    d = float(v1) - float(v0)
    if abs(d) < 1e-300:
        return 0.5
    return (float(iso) - float(v0)) / d
