"""Sommerfeld's half-plane, Penney & Price's water waves, and the fan a bay needs.

WAVE 10, GAP 3. The largest single unbuilt piece of water physics in this
project, and the reason it had to be built is wave 9's proof rather than
anybody's taste for Fresnel integrals:

    At static equilibrium the shoreline is normal to the wave orthogonal at
    every station, so the longshore transport vanishes. Under PLANE crests
    Snell forces theta_0,local = 0 at every station, and integrating that gives
    exactly ONE zero-transport plan-form -- a straight line rotated to face the
    swell. A curved static-equilibrium bay CANNOT EXIST under a ray model with
    plane crests. It exists only where the orthogonal FANS alongshore, and the
    fan is DIFFRACTION.

Wave 9 supplied the fan by hand -- a stated per-row offshore direction radiating
from the bay's own pole -- and got the residual obliquity from 5.595 to 2.801
deg. This module makes the fan an OUTPUT of a wave solution.

WHAT IS IMPORTED AND WHAT IS BUILT. `references/12-water-rendering.md`'s
diffraction section already prices this term for the isolated-rock case and
carries FOUR numbers: K_d = 0.5000 exactly on the geometric shadow boundary, and
K_d = 0.31 / 0.20 / 0.11 at Fresnel parameters v = 0.5 / 1 / 2 into the shadow;
plus a lee centre-line table behind an obstacle of width W. Those are the
chapter's, they are the target, and this file reproduces them from an
implementation that shares no line with the one that produced them. What the
chapter does NOT carry, and what this file adds, is the DIRECTION field: K_d is
an amplitude, and a bay is held by an angle.

THE SOLUTION. Sommerfeld (1896) solved the half-plane exactly -- the first exact
solution of any diffraction problem -- and Penney & Price (1952) applied it to
water waves behind a breakwater. With a time convention exp(-i omega t), a
screen occupying phi = +-pi (a half-line from the origin), and a unit plane wave
arriving FROM the direction phi_0:

    u(r, phi) = U(r, phi - phi_0)  +  s * U(r, phi + phi_0)

    U(r, psi) = (1/sqrt 2) e^(-i pi/4) [ (1+i)/2 + C(X) + i S(X) ] e^(-i k r cos psi)
    X(r, psi) = 2 sqrt(k r / pi) cos(psi/2)

with C, S the Fresnel integrals and s = +1 for a rigid (Neumann) screen, which
is the water-wave case -- no flow through a breakwater or a headland. The first
term is the incident wave, switched off across the geometric SHADOW boundary;
the second is the reflected wave, switched off across the REFLECTION boundary.
Both switch through exactly 1/2 at their own boundary, which is where the
chapter's 0.5000 comes from and it is not a coincidence: X = 0 there, the
Fresnel integral is half its total, and the Cornu spiral's own limits are what
make the total (1+i)/2.

THE DIRECTION IS THE POINT. u is complex, so

    k_vec = grad(arg u) = Im( grad(u) / u )

is the local wavenumber vector -- an OUTPUT of the wave solution, with no stated
per-row direction anywhere in it. Deep in the shadow it is radial from the tip,
which is why a diffracting headland is the "virtual source the fan converges
on"; near the shadow boundary it is not, and the difference is what this wave
measures.

THE STANDING RULING HOLDS. The wave field still arrives from OUTSIDE with a
stated offshore spectrum (H0, T, theta_0). What this module computes is what an
edge does to that stated field before it reaches the domain's offshore boundary;
everything from the boundary shoreward -- shoaling, refraction, breaking -- stays
`transform_2d`'s output.
"""
import math

import numpy as np

# --------------------------------------------------------------- Fresnel C, S
#
# THREE ROUTES, AND THE SUITE COMPARES THEM. There is no scipy in this
# container, so the Fresnel integrals are built here; a single route would be a
# single point of failure under the one thing the whole module rests on.
#
#   * the POWER SERIES, exact for small argument and hopeless above |x| ~ 2
#     because the terms grow to e^39 before they cancel;
#   * GAUSS-LEGENDRE on the defining integral, after scaling the interval to
#     [0, 1] so the node count is fixed;
#   * the ASYMPTOTIC series from repeated integration by parts, which is the
#     only one that works where the physics actually lives (k r of order 10^3,
#     so X of order 30).
#
# The switch is at |x| = 4 and the suite checks the two routes agree there.
_GL_N = 96
_GL_X, _GL_W = np.polynomial.legendre.leggauss(_GL_N)
_GL_X = 0.5 * (_GL_X + 1.0)          # nodes on [0, 1]
_GL_W = 0.5 * _GL_W
_X_SWITCH = 4.0


def _fresnel_gl(x):
    """F(x) = int_0^x exp(i pi t^2 / 2) dt by Gauss-Legendre.

    t = x s puts the integral on [0, 1] with the oscillation entirely in the
    exponent: F = x * sum_j w_j exp(i pi x^2 s_j^2 / 2). At |x| = 4 the phase
    sweeps 25 rad, about four oscillations, which 96 nodes resolve to machine
    precision -- checked against the series below rather than asserted.
    """
    x = np.asarray(x, float)
    ph = 0.5 * math.pi * (x[..., None] ** 2) * (_GL_X ** 2)
    return x * np.sum(_GL_W * np.exp(1j * ph), axis=-1)


def _fresnel_series(x, n_max=120):
    """The power series, term by term. C = sum (-1)^n (pi/2)^(2n) x^(4n+1) /
    ((2n)! (4n+1)), S = sum (-1)^n (pi/2)^(2n+1) x^(4n+3) / ((2n+1)! (4n+3)).

    Written from the definition by expanding exp(i pi t^2/2) and integrating
    term by term, which is a different route from the quadrature and not a
    different spelling of it."""
    x = np.asarray(x, float)
    C = np.zeros_like(x)
    S = np.zeros_like(x)
    a = 0.5 * math.pi
    tc = x.copy()                                    # (pi/2)^0 x^1 / 0!
    for n in range(n_max):
        C = C + ((-1) ** n) * tc / (4 * n + 1)
        ts = tc * a * x ** 2 / (2 * n + 1)
        S = S + ((-1) ** n) * ts / (4 * n + 3)
        tc = ts * a * x ** 2 / (2 * n + 2)
    return C + 1j * S


def _fresnel_asym(x, n_max=24):
    """The asymptotic form, from repeated integration by parts of the tail.

        int_x^inf e^(i pi t^2/2) dt = e^(i pi x^2/2) * [ f(x) + i g(x) ] * ...

    Concretely: with I(x) = int_x^inf, one integration by parts gives
    I = -e^(i pi x^2/2)/(i pi x) + (1/(i pi)) int_x^inf e^(i pi t^2/2)/t^2 dt,
    and iterating produces the divergent-but-asymptotic series summed here to
    its smallest term. F(x) = (1+i)/2 - I(x).

    THIS IS THE ROUTE THE PHYSICS USES. On this scene k r reaches ~10^3 and X
    reaches ~30; the series overflows and the quadrature would need thousands
    of nodes, while here the first neglected term is (1/(pi x^2))^n n! and at
    x = 4 that bottoms out near 1e-13.
    """
    x = np.asarray(x, float)
    sgn = np.sign(x)
    ax = np.abs(x)
    ax = np.maximum(ax, 1e-12)
    z = 1.0 / (1j * math.pi * ax * ax)
    term = np.ones_like(ax, dtype=complex)
    tot = np.zeros_like(ax, dtype=complex)
    prev = np.full(ax.shape, np.inf)
    for n in range(n_max):
        mag = np.abs(term)
        upd = mag < prev                       # stop each element at its own
        tot = np.where(upd, tot + term, tot)   # smallest term
        prev = np.where(upd, mag, prev)
        term = term * z * (2 * n + 1)
    I = -np.exp(0.5j * math.pi * ax * ax) / (1j * math.pi * ax) * tot
    F = (0.5 + 0.5j) - I
    return sgn * F


def fresnel(x):
    """F(x) = C(x) + i S(x) = int_0^x exp(i pi t^2 / 2) dt.

    ODD IN x, and that is not a convenience: the Cornu spiral runs from
    -(1+i)/2 to +(1+i)/2 and its two limits are what put the 1/2 on the shadow
    boundary. The suite checks the oddness, the limits, the derivative and the
    agreement of the three routes."""
    x = np.asarray(x, float)
    out = np.empty(x.shape, complex) if x.ndim else np.empty((), complex)
    small = np.abs(x) <= _X_SWITCH
    if np.any(small):
        out[small] = _fresnel_gl(x[small]) if x.ndim else _fresnel_gl(x)
    if np.any(~small):
        out[~small] = (_fresnel_asym(x[~small]) if x.ndim
                       else _fresnel_asym(x))
    return out if x.ndim else complex(out)


def cornu_limit():
    """(C, S) at +infinity, evaluated rather than quoted. Both are 1/2."""
    v = fresnel(np.array([1e8]))[0]
    return float(v.real), float(v.imag)


def knife_edge_kd(v):
    """The classic knife-edge diffraction coefficient at Fresnel parameter v.

        K_d(v) = | (1+i)/2 * int_v^inf exp(-i pi t^2 / 2) dt |

    v > 0 is INTO the geometric shadow. K_d(0) = 1/2 exactly -- that is
    chapter 12's 0.5000, and the chapter's 0.31 / 0.20 / 0.11 at v = 0.5 / 1 / 2
    are this function at those arguments.

    v IS THE SAME PARAMETER AS THIS FILE'S X, up to a sign: for a plane wave
    past an edge, a point a perpendicular distance b beyond the shadow boundary
    at range r from the tip has v = b sqrt(2 / (lambda r)), and expanding
    X = 2 sqrt(kr/pi) cos(psi/2) about psi = pi with b = r*(psi - pi) gives
    X = -b sqrt(2/(lambda r)) = -v. The suite checks that expansion numerically
    instead of trusting the algebra.
    """
    v = np.asarray(v, float)
    tail = np.conj((0.5 + 0.5j) - fresnel(v))
    return np.abs((0.5 + 0.5j) * tail)


def fresnel_parameter(b, r, lam):
    """v = b sqrt(2 / (lambda r)) -- perpendicular offset b beyond the shadow
    boundary, range r from the tip, wavelength lambda. Positive into shadow."""
    return np.asarray(b, float) * np.sqrt(2.0 / (float(lam)
                                                 * np.asarray(r, float)))


# ------------------------------------------------------- Sommerfeld half-plane
NEUMANN = +1.0          # rigid screen, dphi/dn = 0. THE WATER-WAVE CASE: no
                        # flow through a breakwater or a headland, so the
                        # reflected term ADDS. Penney & Price 1952.
DIRICHLET = -1.0        # u = 0 on the screen. Kept because it is one sign and
                        # because the suite fires it as a defect: it puts a
                        # node on the screen face where the water-wave problem
                        # has an antinode, and it does NOT move the deep-shadow
                        # direction field at all -- which is worth knowing.


def _U(kr, psi):
    """One Sommerfeld term: a plane wave switched off across psi = +-pi.

    U -> exp(-i k r cos psi) where cos(psi/2) > 0 and kr is large;
    U -> 0 where cos(psi/2) < 0;
    U  = exp(-i k r cos psi) / 2 exactly where cos(psi/2) = 0.

    The third line is the whole of chapter 12's "exactly half the incident
    amplitude on the geometric shadow boundary", and it holds at EVERY kr, not
    only asymptotically -- X = 0 there and F(0) = 0 exactly.
    """
    kr = np.asarray(kr, float)
    psi = np.asarray(psi, float)
    X = 2.0 * np.sqrt(np.maximum(kr, 0.0) / math.pi) * np.cos(0.5 * psi)
    br = (0.5 + 0.5j) + fresnel(X)
    return (br * np.exp(-0.25j * math.pi) / math.sqrt(2.0)
            * np.exp(-1j * kr * np.cos(psi)))


def halfplane_polar(kr, phi, phi0, screen=NEUMANN):
    """Sommerfeld's exact half-plane field in the screen's own polar frame.

    kr   : k * r, the range from the edge in radians of phase
    phi  : polar angle of the field point, in (-pi, pi]; the screen is phi = pi
    phi0 : the direction the unit incident plane wave arrives FROM, (-pi, pi)

    Unit incident amplitude, so |u| IS K_d.

    THE SECOND TERM'S ARGUMENT IS 2 pi - phi - phi_0 AND NOT phi + phi_0, and
    the first draft of this file had it the other way round. Both give the same
    plane wave -- cos(2 pi - phi - phi_0) = cos(phi + phi_0) -- but they switch
    it on in COMPLEMENTARY regions, and `phi + phi_0` puts the reflected wave
    everywhere except the region where reflection happens, which is
    catastrophic and completely invisible in a plot of the shadow. What caught
    it was the 1/2 on the shadow boundary reading 1.1, 0.61, 1.32 instead: the
    reflected term was standing at full strength where it should have been
    zero. Sommerfeld's U is 4 pi-periodic, so 2 pi - psi is the OTHER SHEET of
    the same function, which is the whole content of "the half-plane problem
    lives on a two-sheeted Riemann surface".

    With this form both faces of the screen satisfy the Neumann condition
    exactly for screen = +1 and the Dirichlet condition exactly for -1, because
    the two arguments COINCIDE at phi = +-pi while their phi-derivatives are
    equal and opposite. The suite measures both rather than taking the algebra
    on trust.
    """
    phi = np.asarray(phi, float)
    return (_U(kr, phi - phi0)
            + float(screen) * _U(kr, 2.0 * math.pi - phi - phi0))


def shadow_boundary_angle(phi0):
    """The polar angle of the geometric shadow boundary. The incident term
    switches off where |phi - phi0| = pi."""
    return phi0 + math.pi if phi0 <= 0.0 else phi0 - math.pi


def reflection_boundary_angle(phi0):
    """The polar angle of the reflected-wave boundary. The reflected term is on
    between here and the screen, i.e. where |phi + phi_0| > pi."""
    return math.pi - phi0 if phi0 >= 0.0 else -math.pi - phi0


class Edge:
    """A diffracting edge in SCENE coordinates: a tip, a screen bearing, an
    incident direction and a wavenumber.

    tip        : (x, y) m, the diffraction point
    screen_dir : unit (x, y), the direction the semi-infinite screen extends
                 FROM the tip. For a headland this is the headland's own
                 updrift shoreline bearing; nothing is placed by hand.
    khat       : unit (x, y), the direction the incident wave TRAVELS
    k          : rad/m

    ONE CODE PATH. Every edge this project stamps -- at the true headland tip,
    at the bay's own pole, at an isolated rock -- is this class with different
    arguments, and the suite fires all of them through the same `field`.
    """

    def __init__(self, tip, screen_dir, khat, k, screen=NEUMANN):
        self.tip = np.asarray(tip, float)
        s = np.asarray(screen_dir, float)
        self.screen_dir = s / np.hypot(s[0], s[1])
        e = np.asarray(khat, float)
        self.khat = e / np.hypot(e[0], e[1])
        self.k = float(k)
        self.screen = float(screen)
        # the local frame: +x_local is OPPOSITE the screen, so the screen sits
        # at phi = +-pi exactly as Sommerfeld's solution wants it.
        self.ex = -self.screen_dir
        self.ey = np.array([-self.ex[1], self.ex[0]])
        self.phi0 = math.atan2(float(np.dot(-self.khat, self.ey)),
                               float(np.dot(-self.khat, self.ex)))
        self.phi_sb = shadow_boundary_angle(self.phi0)
        self.phi_rb = reflection_boundary_angle(self.phi0)

    # ---- geometry
    def polar(self, X, Y):
        """(r, phi) of scene points about the tip, in the local frame."""
        dx = np.asarray(X, float) - self.tip[0]
        dy = np.asarray(Y, float) - self.tip[1]
        u = dx * self.ex[0] + dy * self.ex[1]
        v = dx * self.ey[0] + dy * self.ey[1]
        return np.hypot(u, v), np.arctan2(v, u)

    def in_shadow(self, X, Y):
        """The GEOMETRIC shadow -- what a ray model would leave empty. The
        incident term's switch, as a boolean, so the figure can draw the
        boundary a ray model believes in and the field that ignores it."""
        _, phi = self.polar(X, Y)
        return np.abs(phi - self.phi0) > math.pi

    def shadow_boundary_line(self, t):
        """Points along the geometric shadow boundary: the ray that grazes the
        tip. t is metres from the tip."""
        t = np.asarray(t, float)
        return (self.tip[0] + t * self.khat[0], self.tip[1] + t * self.khat[1])

    # ---- the field
    def field(self, X, Y):
        """The complex diffracted field at scene points, unit incident."""
        r, phi = self.polar(X, Y)
        return halfplane_polar(self.k * r, phi, self.phi0, self.screen)

    def kd(self, X, Y):
        """|u| -- the diffraction coefficient. 1 far in the lit region, 1/2 on
        the geometric shadow boundary, falling into the shadow."""
        return np.abs(self.field(X, Y))

    def wave_vector(self, X, Y, step=None):
        """k_vec = grad(arg u) = Im(grad u / u), in scene coordinates.

        THE FAN, AS AN OUTPUT. Central differences on the complex field rather
        than on the wrapped phase, because arg() jumps by 2 pi and the
        difference of two complex numbers does not. `step` defaults to
        lambda/400, which is far above the 1e-8 where the Fresnel routes stop
        agreeing and far below any scale in the field.
        """
        if step is None:
            step = 2.0 * math.pi / self.k / 400.0
        X = np.asarray(X, float)
        Y = np.asarray(Y, float)
        u = self.field(X, Y)
        ux = (self.field(X + step, Y) - self.field(X - step, Y)) / (2 * step)
        uy = (self.field(X, Y + step) - self.field(X, Y - step)) / (2 * step)
        kx = np.imag(ux / u)
        ky = np.imag(uy / u)
        return kx, ky

    def direction(self, X, Y, step=None):
        """The local propagation direction, radians from +x. `transform_2d`
        takes exactly this as its per-row offshore theta_0."""
        kx, ky = self.wave_vector(X, Y, step=step)
        return np.arctan2(ky, kx)

    def wavenumber_ratio(self, X, Y, step=None):
        """|k_vec| / k. One where the field is locally a plane wave; it
        departs where two terms of comparable size interfere, and reporting it
        is how a reader knows when the direction above is meaningful."""
        kx, ky = self.wave_vector(X, Y, step=step)
        return np.hypot(kx, ky) / self.k


# ---------------------------------------------------- the two edges this scene
def headland_edge(ep, k, coast_bearing=None):
    """THE EDGE GAP 3 NAMES: stamped at the true headland tip.

    `ep` is `beach.equilibrium_plan()`. The tip is A1, the updrift rock anchor
    -- the seaward-most shoreline point in the outer quarter of the frame, which
    the coastal loop produced and nothing placed. The screen is the headland's
    own updrift shoreline, whose bearing is measured from the loop's plan-form
    rather than declared, unless one is passed for a test.

    THIS EDGE IS WHERE THE GAP'S OWN PRESCRIPTION GOES TO BE MEASURED, and the
    measurement is the finding. Read `README-beach.md` W-section before reusing
    it as if it worked.
    """
    A1 = np.asarray(ep['A1'], float)
    if coast_bearing is None:
        y = np.asarray(ep['y'], float)
        xs = np.asarray(ep['x_s_rock'], float)
        j1 = int(ep['j1'])
        lo = max(j1 - 8, 0)
        if j1 - lo >= 2:
            p = np.polyfit(y[lo:j1 + 1], xs[lo:j1 + 1], 1)
            b = np.array([p[0], 1.0])
        else:
            b = np.array([0.0, 1.0])
        b = -b / np.hypot(b[0], b[1])      # updrift is -y
    else:
        b = np.asarray(coast_bearing, float)
    return Edge(A1, b, np.asarray(ep['khat'], float), k)


def pole_edge(ep, k, screen_dir=None):
    """THE EDGE THE CONSTRUCTION'S OWN DEFINITION NAMES: stamped at the pole.

    `12a` section 11 defines the pole as "the diffraction point, or more
    generally the virtual source the fan converges on", and `spiral_pole`'s
    selection rule is "the pole is the sheltering headland's diffraction point,
    and a pole 79 km offshore is not a headland". So the construction already
    ASSERTS that an edge sits at D. Stamping a real Sommerfeld edge there turns
    that assertion into a test: wave 9's fan is a pure radial fan of unit
    amplitude from D, and the Sommerfeld solution at the same point supplies the
    same radial directions in the deep shadow PLUS an amplitude field, a finite
    transition across the shadow boundary and the Fresnel oscillations in the
    lit region. If those extras do not matter the two rows agree; if they do,
    the difference is the physics wave 9 did not have.

    The screen extends from D on the UPDRIFT side, perpendicular to the
    incident direction -- the orientation that makes D the tip of a sheltering
    barrier rather than a barrier the swell runs along. It is one choice out of
    a one-parameter family and the suite reports the field's sensitivity to it.
    """
    D = np.asarray(ep['D'], float)
    kh = np.asarray(ep['khat'], float)
    if screen_dir is None:
        screen_dir = np.array([kh[1], -kh[0]])     # 90 deg updrift of khat
    return Edge(D, screen_dir, kh, k)


def diffracted_boundary(edge, x_off, y, H0):
    """The offshore boundary condition a diffracting edge delivers.

    Returns per-alongshore-row (theta_0, H_0, K_d) at the domain's offshore
    boundary x = x_off. Both are OUTPUTS of the wave solution; the only stated
    quantities are the offshore spectrum's own H0, T, theta_0 and the edge's
    geometry.

    K_d MULTIPLIES THE HEIGHT AND THAT IS NOT FREE. Q goes as H_b^(5/2), so a
    shadow that halves the height cuts the transport by 5.7x for a reason that
    has nothing to do with the shoreline being an equilibrium. Every row this
    file reports is run BOTH ways -- direction only, and direction with
    amplitude -- because a transport that falls because the waves got smaller is
    not a bay reaching equilibrium, and conflating the two is a way a
    measurement lies.
    """
    y = np.asarray(y, float)
    X = np.full(y.size, float(x_off))
    kd = edge.kd(X, y)
    th = edge.direction(X, y)
    return dict(theta0=th, H0=float(H0) * kd, kd=kd,
                H0_plain=np.full(y.size, float(H0)),
                kr=edge.k * edge.polar(X, y)[0],
                phi=edge.polar(X, y)[1],
                shadow=edge.in_shadow(X, y))


# ------------------------------------------------------ the independent checks
def helmholtz_residual(edge, X, Y, step=None):
    """|(lap + k^2) u| / (k^2 |u|) on a 4th-order stencil.

    THE CHECK THAT CAN ACTUALLY FAIL. Sommerfeld's formula is exact, so the
    residual measures the Fresnel integrals, the branch handling and the frame
    conversion all at once. A wrong Fresnel route, a wrapped phi, a sign on the
    reflected term -- any of them shows up here and none of them shows up in a
    picture of |u|.
    """
    if step is None:
        step = 2.0 * math.pi / edge.k / 60.0
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    u0 = edge.field(X, Y)

    def lap(axis):
        o = [step * (axis == 0), step * (axis == 1)]
        f = [edge.field(X + m * o[0], Y + m * o[1]) for m in (-2, -1, 1, 2)]
        return (-f[0] + 16 * f[1] - 30 * u0 + 16 * f[2] - f[3]) / (12 * step ** 2)

    res = lap(0) + lap(1) + edge.k ** 2 * u0
    return np.abs(res) / (edge.k ** 2 * np.abs(u0))


def screen_normal_derivative(edge, s, eps=None):
    """(1/r) du/dphi at phi = pi - eps and -pi + eps, s metres from the tip.

    The Neumann boundary condition, which is the whole difference between a
    breakwater and a pressure release. Reported as |du/dn| / (k |u|) so it is
    dimensionless and comparable across ranges.
    """
    if eps is None:
        eps = 1e-4
    s = np.asarray(s, float)
    out = []
    for side in (+1.0, -1.0):
        ph = side * (math.pi - eps)
        dph = 1e-6
        u1 = halfplane_polar(edge.k * s, ph - side * dph, edge.phi0,
                             edge.screen)
        u2 = halfplane_polar(edge.k * s, ph + side * dph, edge.phi0,
                             edge.screen)
        du = (u2 - u1) / (2 * dph) / s
        u0 = halfplane_polar(edge.k * s, ph, edge.phi0, edge.screen)
        out.append(np.abs(du) / (edge.k * np.abs(u0)))
    return out


def flux_x(edge, x0, y, step=None):
    """The x-component of the wave energy flux across a line x = x0, as
    Im(conj(u) du/dx) / k, integrated over the sampled y.

    ENERGY HAS TO COME FROM SOMEWHERE. Between two lines downwave of the tip
    there is no screen and no source, so the integrated flux must be the same
    through both -- and it is the only statement in this file that ties the
    energy appearing in the geometric shadow to the energy missing from the lit
    side. A one-sided check on |u| cannot make it.
    """
    if step is None:
        step = 2.0 * math.pi / edge.k / 400.0
    y = np.asarray(y, float)
    X = np.full(y.size, float(x0))
    u = edge.field(X, y)
    ux = (edge.field(X + step, y) - edge.field(X - step, y)) / (2 * step)
    f = np.imag(np.conj(u) * ux) / edge.k
    return float(np.trapezoid(f, y))


def lee_centreline(w_over_lam, n_dist=7, lam=1.0):
    """Chapter 12's own lee centre-line table, recomputed here.

    The chapter gives, behind an obstacle of width W on the lee centre line and
    for unit incident amplitude:

        distance / (W^2/lam)   0.1   0.25   0.5    1    2    4   10
        amplitude              0.20  0.31   0.41  0.51 0.62 0.71 0.80

    An obstacle has TWO edges, and on the centre line they are equidistant, so
    the two half-plane fields arrive in phase and add. Each is at Fresnel
    parameter v = (W/2) sqrt(2 / (lam r)). This function is the coherent sum,
    2 K_d(v), and reproducing the chapter's row is the import check: if it
    disagrees, either this file's Fresnel integrals are wrong or the chapter's
    convention is not the one stated, and either is worth knowing.
    """
    W = float(w_over_lam) * float(lam)
    frac = np.array([0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 10.0])[:n_dist]
    r = frac * W ** 2 / float(lam)
    v = fresnel_parameter(0.5 * W, r, lam)
    return dict(frac=frac, r=r, v=v, amp=2.0 * knife_edge_kd(v))
