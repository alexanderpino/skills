#!/usr/bin/env python3
"""mu_d just below a flat surface, for a UNIFORM sky and for the CIE STANDARD OVERCAST sky.

`water-optics.md` prints 0.86 and labels it a *uniform* overcast sky, in two places, and feeds
it to K_d. A uniform sky and the standard overcast sky are not the same distribution, and this
rig exists to say which number belongs to which.

mu_d is the average cosine of the downwelling field: E_d / E_0d, both taken just below the
surface. Refraction compresses the whole sky into Snell's cone (48.6 deg at n = 1.335), so mu_d
is high whatever the sky does; the question is only how high.

Method, no radiative-transfer library: take the sky as azimuthally symmetric, refract each ring
through the interface, and conserve the beam.

  dE_d  = L(t_s) * T(t_s) * cos(t_s) dOmega_s          transmitted irradiance of the ring
  dE_0d = dE_d / cos(t_w)                              same beam, divided by its own cosine

  mu_d  = INT L T cos(t_s) dOmega_s  /  INT L T cos(t_s)/cos(t_w) dOmega_s

with sin(t_s) = n sin(t_w) (Snell) and T = 1 - R, R the unpolarised Fresnel reflectance
(mean of the two polarisations). dOmega_s = 2 pi sin(t_s) dt_s.

Skies:
  uniform            L(t) = 1                      (isotropic; what the page's word says)
  standard overcast  L(t) = (1 + 2 cos t) / 3      (CIE / Moon-Spencer; three times brighter
                                                    at the zenith than at the horizon)

Halting: one fixed-count Simpson quadrature, no loop with a data-dependent bound. Refinement is
a convergence report, not a search.
"""
import math

N_REF = 1.335   # sea water, ~550 nm, the value water-optics.md uses


def fresnel_T(theta_s: float, n: float = N_REF) -> float:
    """Unpolarised transmittance, air -> water, at incidence theta_s from the normal."""
    cs = math.cos(theta_s)
    s = math.sin(theta_s) / n
    if s >= 1.0:
        return 0.0
    cw = math.sqrt(1.0 - s * s)
    rs = ((cs - n * cw) / (cs + n * cw)) ** 2
    rp = ((n * cs - cw) / (n * cs + cw)) ** 2
    return 1.0 - 0.5 * (rs + rp)


def mu_d(sky, n: float = N_REF, m: int = 200000) -> float:
    """Simpson over theta_s in [0, pi/2]. m must be even."""
    num = den = 0.0
    h = (math.pi / 2) / m
    for i in range(m + 1):
        ts = i * h
        w = 1.0 if i in (0, m) else (4.0 if i % 2 else 2.0)
        cs, ss = math.cos(ts), math.sin(ts)
        cw = math.sqrt(max(0.0, 1.0 - (ss / n) ** 2))
        f = sky(ts) * fresnel_T(ts, n) * cs * ss     # the 2*pi and the h/3 cancel in the ratio
        num += w * f
        den += w * (f / cw if cw > 0 else 0.0)
    return num / den


SKIES = {
    "uniform (isotropic)":            lambda t: 1.0,
    "CIE standard overcast":          lambda t: (1.0 + 2.0 * math.cos(t)) / 3.0,
}

if __name__ == "__main__":
    print(f"n = {N_REF}, Snell cone half-angle = {math.degrees(math.asin(1.0/N_REF)):.2f} deg\n")
    out = {}
    for name, sky in SKIES.items():
        out[name] = mu_d(sky)
        print(f"  mu_d  {name:<26} {out[name]:.4f}")

    u = out["uniform (isotropic)"]
    c = out["CIE standard overcast"]
    print(f"\n  gap = {c - u:+.4f}  ({(c/u - 1)*100:+.2f}%)")
    print(f"  rounded to 2 dp: uniform {u:.2f}, standard overcast {c:.2f}")

    print("\n  convergence (uniform sky, Simpson m):")
    for m in (2000, 20000, 200000):
        print(f"    m = {m:>7}  mu_d = {mu_d(SKIES['uniform (isotropic)'], m=m):.6f}")

    print("\n  sensitivity to n:")
    for n in (1.330, 1.335, 1.340):
        print(f"    n = {n:.3f}  uniform {mu_d(SKIES['uniform (isotropic)'], n=n):.4f}"
              f"   overcast {mu_d(SKIES['CIE standard overcast'], n=n):.4f}")

    print("\n  no-Fresnel control (T = 1, refraction only):")
    for name, sky in SKIES.items():
        num = den = 0.0
        m, h = 200000, (math.pi / 2) / 200000
        for i in range(m + 1):
            ts = i * h
            w = 1.0 if i in (0, m) else (4.0 if i % 2 else 2.0)
            cs, ss = math.cos(ts), math.sin(ts)
            cw = math.sqrt(max(0.0, 1.0 - (ss / N_REF) ** 2))
            f = sky(ts) * cs * ss
            num += w * f
            den += w * f / cw
        print(f"    {name:<26} {num/den:.4f}")
