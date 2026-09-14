"""water-rendering.md -- price the (A, A^2) prefilter pair, and re-check the error half it is
paired with.

RIG: CPython 3 + numpy on a shared Linux container. Deterministic; NO wall-clock timing is taken
and none is printed, because a CPython timing is not a GPU frame cost. Everything below is either
(i) exact storage arithmetic over IEEE formats, or (ii) a fixed-seed numerical experiment. Both
reproduce bit-for-bit across runs -- the point of printing them rather than a millisecond.

Part 1  STORAGE: what R32G32F costs against the fp16 pair, per cell, with and without the mip
        chain the prefilter requires. Channel widths come from numpy's own itemsize, not from
        memory.
Part 2  ERROR (re-check of figures ALREADY on the page): offset-centred fp16 recovery of sigma_A
        at 3, 10 and 30 sigma of offset, through the pairwise 2x2 averaging that hardware
        mipmapping actually performs, against a float64 reference. 20 seeds, as the page claims.

Usage:  python3 water-rendering.py
"""
import numpy as np

SEEDS = range(20)
FOOT = 64          # 64x64 footprint: the largest the page's own 8x8 -> 64x64 range names
SIGMA = 0.01       # the page's worked sigma_A


def mip_mean_fp16(a):
    """Average a 2^k x 2^k fp16 array to a scalar the way hardware mipmapping does:
    repeated 2x2 box filters, every intermediate stored back in fp16."""
    x = a.astype(np.float16)
    while x.shape[0] > 1:
        x = ((x[0::2, 0::2].astype(np.float16) + x[0::2, 1::2] +
              x[1::2, 0::2] + x[1::2, 1::2]) * np.float16(0.25)).astype(np.float16)
    return np.float64(x[0, 0])


def recover_sigma_fp16(A, offset):
    """Offset-centred pair: store (A-offset) and (A-offset)^2 in fp16, mip both, recombine."""
    b = (A - offset).astype(np.float16)
    b2 = (b.astype(np.float64) ** 2).astype(np.float16)
    mu = mip_mean_fp16(b)
    m2 = mip_mean_fp16(b2)
    return np.sqrt(max(m2 - mu * mu, 0.0))


def recover_sigma_fp64(A, offset):
    b = (A.astype(np.float64) - offset)
    mu = b.mean()
    m2 = (b * b).mean()
    return np.sqrt(max(m2 - mu * mu, 0.0))


def part1_storage():
    print("PART 1  STORAGE  (exact; IEEE widths from numpy itemsize)")
    h = np.dtype(np.float16).itemsize
    f = np.dtype(np.float32).itemsize
    print(f"  float16 itemsize = {h} bytes      float32 itemsize = {f} bytes")
    pair16, pair32 = 2 * h, 2 * f
    print(f"  (A, A^2) pair, fp16 (RG16F)   = {pair16} bytes per cell")
    print(f"  (A, A^2) pair, fp32 (R32G32F) = {pair32} bytes per cell     ratio = {pair32/pair16:.0f}x")
    # A full 2D mip chain adds 1/4 + 1/16 + ... -> 1/3 of the base, in the limit.
    chain = sum(0.25 ** k for k in range(1, 40))
    print(f"  full 2D mip chain multiplier  = 1 + {chain:.6f} = {1+chain:.6f}  (limit 4/3)")
    print(f"  mipped fp16 pair   = {pair16*(1+chain):.2f} bytes per cell")
    print(f"  mipped fp32 pair   = {pair32*(1+chain):.2f} bytes per cell")
    for n in (1024, 2048, 4096):
        mb16 = pair16 * (1 + chain) * n * n / 1024 ** 2
        mb32 = pair32 * (1 + chain) * n * n / 1024 ** 2
        print(f"  at {n}^2 mipped: fp16 {mb16:7.2f} MB   fp32 {mb32:7.2f} MB   delta {mb32-mb16:7.2f} MB")


def part2_error():
    print("PART 2  ERROR  (re-check of figures already on the page)")
    print("  model: A ~ N(1 + k*sigma, sigma), sigma = %.3g, footprint %dx%d, 20 seeds" % (SIGMA, FOOT, FOOT))
    print("  k    amplification 1+k^2   mean |rel err| in sigma_A   worst over seeds")
    for k in (3, 10, 30):
        errs = []
        for s in SEEDS:
            rng = np.random.default_rng(s)
            A = rng.normal(1.0 + k * SIGMA, SIGMA, size=(FOOT, FOOT))
            ref = recover_sigma_fp64(A, 1.0)
            got = recover_sigma_fp16(A, 1.0)
            errs.append(abs(got - ref) / ref)
        errs = np.array(errs)
        print(f"  {k:<4} {1+k*k:<21} {100*errs.mean():>8.2f}%                  {100*errs.max():>8.2f}%")
    # the uncentred pair, for the contrast the page draws
    errs = []
    for s in SEEDS:
        rng = np.random.default_rng(s)
        A = rng.normal(1.0, SIGMA, size=(FOOT, FOOT))
        ref = recover_sigma_fp64(A, 0.0)
        got = recover_sigma_fp16(A, 0.0)
        errs.append(got)
    print(f"  uncentred pair on calm water (mu_A = 1, sigma = {SIGMA}): recovered sigma_A"
          f" = {np.mean(errs):.3f} (page says 0.000)")


if __name__ == "__main__":
    part1_storage()
    print()
    part2_error()
