"""Dimensional-consistency audit of the load-bearing equations, machine-checked with `pint`.

A dimensionally-inconsistent equation is invalid, full stop — so this is genuine (necessary,
not sufficient) evidence of validity, not self-consistency. Two grades of check:

  * DECISIVE — the equation is built from constants with INDEPENDENTLY-KNOWN units (g, rho,
    Glen's A, viscosity eta). If an exponent or factor were wrong, the result dimension would
    be wrong and the test fails. These actually test the physics.
  * CONFIRMATORY — a phenomenological constant (stream-power K, hillslope D) whose units are
    DEFINED by the equation. The check confirms the STATED units are self-consistent (catches a
    mis-stated unit) but cannot fail on the physics. Marked as such.

Optional (pint), like the cross-validation tests: skips cleanly if pint isn't installed.
Install: pip install -r requirements-validate.txt
"""
import pytest

pint = pytest.importorskip("pint")
u = pint.UnitRegistry()

L_T = "[length] / [time]"
PA = u.Pa
L2_T = "[length] ** 2 / [time]"


# --------------------------------------------------------------------------- #
# DECISIVE — physically-grounded constants; a wrong exponent breaks the dimension
# --------------------------------------------------------------------------- #
def test_pipe_and_lava_driving_stress_is_pascals():
    """tau = rho * g * L * sin(theta)  (04 pipe, 19 lava). Built from rho, g -> must be Pa."""
    rho = 2600.0 * u.kg / u.m ** 3
    g = 9.81 * u.m / u.s ** 2
    L = 3.0 * u.m
    sin_theta = 0.2 * u.dimensionless
    tau = rho * g * L * sin_theta
    assert tau.check("[pressure]"), tau.to_base_units()


def test_sia_diffusivity_is_area_per_time():
    """D = (2A/(n+2)) (rho g)^n H^(n+2) |grad s|^(n-1)  (12 SIA). Glen's A is Pa^-3 s^-1; the
    H^(n+2) and (rho g)^n exponents are exactly what make this a diffusivity. A DECISIVE test of
    the SIA form — a wrong exponent would not come out as m^2/s."""
    n = 3
    A = 2.4e-24 / u.Pa ** 3 / u.s
    rho = 917.0 * u.kg / u.m ** 3
    g = 9.81 * u.m / u.s ** 2
    H = 200.0 * u.m
    grad = 0.1 * u.dimensionless
    D = (2 * A / (n + 2)) * (rho * g) ** n * H ** (n + 2) * grad ** (n - 1)
    assert D.check(L2_T), D.to_base_units()


def test_lava_bingham_flux_is_area_per_time():
    """q = k (tau - tau_y) L^2 / eta  (19). eta is Pa s; q is flux per unit width -> m^2/s,
    then dL = q dt / cellsize -> m."""
    tau, tau_y = 5000.0 * u.Pa, 1000.0 * u.Pa
    L = 2.0 * u.m
    eta = 1e3 * u.Pa * u.s
    q = (tau - tau_y) * L ** 2 / eta                 # k is dimensionless
    assert q.check(L2_T), q.to_base_units()
    dL = q * (0.1 * u.s) / (20.0 * u.m)
    assert dL.check("[length]"), dL.to_base_units()


def test_voellmy_runout_is_length():
    """L = H / tan(alpha)  (05). tan is dimensionless -> runout is a length."""
    H = 500.0 * u.m
    tan_alpha = 0.5 * u.dimensionless
    assert (H / tan_alpha).check("[length]")


def test_airy_root_is_length():
    """Airy isostatic root r = h * rho_c / (rho_m - rho_c)  (02). Density ratio dimensionless."""
    h = 3000.0 * u.m
    rho_c, rho_m = 2700.0 * u.kg / u.m ** 3, 3300.0 * u.kg / u.m ** 3
    assert (h * rho_c / (rho_m - rho_c)).check("[length]")


def test_tephra_decay_exponent_is_dimensionless():
    """thickness = T0 exp(-k x)  (11, Pyle 1989). The exponent MUST be dimensionless, which
    forces k ~ 1/length — a decisive check on the thinning law's argument."""
    k = 0.001 / u.m
    x = 5000.0 * u.m
    assert (k * x).check(""), (k * x).to_base_units()


def test_age_depth_subsidence_is_length():
    """d = d0 + C sqrt(age)  (12, Parsons & Sclater). C ~ m / sqrt(time) -> depth is a length."""
    d0 = 2500.0 * u.m
    C = 350.0 * u.m / u.Myr ** 0.5
    age = 80.0 * u.Myr
    assert (d0 + C * age ** 0.5).check("[length]")


# --------------------------------------------------------------------------- #
# CONFIRMATORY — phenomenological constants; checks the STATED units are consistent
# --------------------------------------------------------------------------- #
def test_stream_power_rate_is_length_per_time():
    """dh/dt = U - K A^m S^n  (04). K's units (m^(1-2m) yr^-1) are DEFINED to balance this, so
    this confirms the stated K unit is self-consistent — it cannot fail on physics."""
    m_exp = 0.5
    K = 1e-5 * u.m ** (1 - 2 * m_exp) / u.year
    A = 1e6 * u.m ** 2
    S = 0.1 * u.dimensionless
    U = 0.001 * u.m / u.year
    assert (U - K * A ** m_exp * S).check(L_T)


def test_hillslope_diffusion_rate_is_length_per_time():
    """dh/dt = D grad^2 h  (04/05, Culling). D is m^2/time (diffusivity) -> confirms the rate."""
    D = 0.1 * u.m ** 2 / u.year
    lap_h = (1.0 * u.m) / u.m ** 2                    # grad^2 of a height field -> 1/length
    assert (D * lap_h).check(L_T)


# --------------------------------------------------------------------------- #
# HONEST FINDING — TWI's log argument is not dimensionless (a known convention)
# --------------------------------------------------------------------------- #
def test_twi_argument_is_dimensioned_by_convention():
    """TWI = ln(a / tan slope) with a = A / contour-width  (06, Beven & Kirkby 1979). The
    argument a/tan(S) carries units of LENGTH — ln of a dimensioned quantity, which is strictly
    improper. This is a real, documented convention of the index (it implies a hidden reference
    length of 1 m), NOT a transcription error. Recorded here honestly rather than hidden."""
    A = 1e5 * u.m ** 2
    width = 20.0 * u.m
    a = A / width
    tan_s = 0.05 * u.dimensionless
    assert (a / tan_s).check("[length]")             # dimensioned -> the known caveat
