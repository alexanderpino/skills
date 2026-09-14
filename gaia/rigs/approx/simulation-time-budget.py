#!/usr/bin/env python3
"""Re-derive the clamped-accumulator scheduler's tick counts for
gaia/references/simulation-time-budget.md, and the sim-time shortfall they imply.

WHAT THIS RIG IS: exact-rational (fractions.Fraction) arithmetic over the scheduler
described in the document -- per frame, add the elapsed wall time to an accumulator,
clamp the accumulator to N_max*dt, consume whole dt ticks, keep the remainder.
It counts TICKS. Nothing is simulated inside a tick.

WHAT IT IS NOT: not a physics benchmark, not a CPython microbenchmark, not a GPU
frame cost. It produces no milliseconds of machine time and must never be printed
as one. Deterministic: no RNG, no seed (the "jitter" case is a fixed +/-1 ms
alternation, not a random one).

Usage: python3 simulation-time-budget.py
"""
from fractions import Fraction as F


def ticks(fps, seconds=10, dt=F(1, 60), n_max=4, jitter_ms=0):
    """Total ticks consumed over `seconds` of wall clock at a fixed frame rate."""
    frames = seconds * fps
    assert frames == int(frames), "choose a whole number of frames"
    base = F(1, 1) / F(fps)
    cap = n_max * dt
    acc = F(0)
    total = 0
    for i in range(int(frames)):
        sign = 1 if i % 2 == 0 else -1
        acc += base + sign * F(jitter_ms, 1000)
        if acc > cap:
            acc = cap
        n = int(acc / dt)          # whole ticks
        total += n
        acc -= n * dt
    return total


def main():
    dt, n_max, seconds = F(1, 60), 4, 10
    ideal = int(seconds / dt)
    print(f"dt = 1/60 s, N_max = {n_max}, cap = N_max*dt = {float(n_max*dt)*1000:.2f} ms "
          f"of simulated time per frame")
    print(f"ideal ticks in {seconds} s of wall clock = {ideal}")
    print(f"{'case':>16} {'ticks':>6} {'short':>6} {'shortfall':>10}")
    cases = [("60 fps", 60, 0), ("20 fps", 20, 0), ("17 fps", 17, 0), ("16 fps", 16, 0),
             ("15 fps", 15, 0), ("15 fps +/-1ms", 15, 1), ("12 fps", 12, 0), ("8 fps", 8, 0)]
    for name, fps, j in cases:
        t = ticks(fps, seconds, dt, n_max, j)
        print(f"{name:>16} {t:>6} {ideal - t:>6} {100 * (ideal - t) / ideal:>9.1f}%")


if __name__ == "__main__":
    main()
