"""Voellmy runout (05-erosion-thermal-aeolian.md). Voellmy 1955.

Step the failed mass down the steepest-descent path and integrate the equation of motion
IN SPACE (the work-energy form drops the timestep): d(1/2 v^2)/dx = g sin(theta) -
mu g cos(theta) - g v^2 / xi. The mass stops where v reaches zero. For the pure-Coulomb
limit (xi -> inf) energy conservation gives total horizontal runout D = H / mu, i.e. a
reach angle alpha with tan(alpha) = mu (Corominas 1996), which the test checks.
"""
import numpy as np

_SQRT2 = np.sqrt(2.0)
_DIRS = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
         (-1, -1, _SQRT2), (-1, 1, _SQRT2), (1, -1, _SQRT2), (1, 1, _SQRT2)]


def _next_cell(h, i, j, di, dj, cellsize):
    """Pick the next step: the steepest-descent neighbour if any lies downhill, else coast
    straight ahead on momentum (di, dj) — this is what carries the mass across a flat and
    lets it run partway up an opposing wall. Returns (ni, nj, dx, ndi, ndj) or Nones."""
    n, m = h.shape
    best, out = 0.0, None
    for ddi, ddj, dist in _DIRS:
        ni, nj = i + ddi, j + ddj
        if 0 <= ni < n and 0 <= nj < m:
            s = (h[i, j] - h[ni, nj]) / (dist * cellsize)
            if s > best:
                best, out = s, (ni, nj, dist * cellsize, ddi, ddj)
    if out is not None:                             # a genuine downhill step
        return out
    ni, nj = i + di, j + dj                          # flat/uphill: keep momentum
    if 0 <= ni < n and 0 <= nj < m:
        dist = np.hypot(di, dj) * cellsize
        return ni, nj, dist, di, dj
    return None, None, None, None, None


def voellmy_runout(h, start, mu, xi, cellsize=1.0, g=9.81, v0=0.0, init_dir=(0, 1),
                   max_steps=100000):
    """Return the runout track (list of (i, j)) from `start` to where the mass rests."""
    h = np.asarray(h, dtype=np.float64)
    i, j = start
    di, dj = init_dir
    v = float(v0)
    track = [(i, j)]
    for _ in range(max_steps):
        ni, nj, horiz, ndi, ndj = _next_cell(h, i, j, di, dj, cellsize)
        if ni is None:                              # walked off the grid -> rests
            break
        dh = h[i, j] - h[ni, nj]                     # >0 downhill, <0 climbing
        theta = np.arctan2(dh, horiz)
        dx = np.hypot(horiz, dh)                      # ALONG-SLOPE path length (not horizontal)
        a = g * np.sin(theta) - mu * g * np.cos(theta) - g * v * v / xi
        v2 = v * v + 2.0 * a * dx                    # v dv/dx = a  ->  v^2_next = v^2 + 2 a dx
        if v2 <= 0.0:                                # decelerated to rest -> the runout toe
            break
        v = np.sqrt(v2)
        i, j, di, dj = ni, nj, ndi, ndj
        track.append((i, j))
    return track
