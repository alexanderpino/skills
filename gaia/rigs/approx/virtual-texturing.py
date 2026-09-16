#!/usr/bin/env python3
"""Re-derivation of every figure added to gaia/references/virtual-texturing.md.

Nothing here is a benchmark. It is exact integer/rational arithmetic over figures the
document ALREADY prints, run so the orchestrator can re-check them without doing it by
hand. No seed, no randomness, no timing: rerunning gives byte-identical output.

Inputs, and where each one is already on the page (line numbers are the post-edit file):
  page edge      128 texels   -- ":146, 'a few thousand pages of 128^2'"
  pool edge      16384 texels -- ":106, 'A 256k^2 virtual over a 16k^2 pool'"
  virtual edge   262144       -- same line
  bytes/texel    1            -- ":48, 'even at one compressed byte each'"
  world          100 km^2 at 1 texel/cm -- ":47-48"
  feedbackScale  4            -- ":135-136, 'so 4 at quarter res'"
"""
PAGE, POOL, VIRT, BPT = 128, 16 * 1024, 256 * 1024, 1

page_bytes = PAGE * PAGE * BPT
pages_in_pool = (POOL // PAGE) ** 2
pool_bytes = POOL * POOL * BPT
assert pages_in_pool * page_bytes == pool_bytes

print("COST -- resident pool, exact integer arithmetic")
print(f"  one {PAGE}^2 page at {BPT} byte/texel        = {page_bytes} B = {page_bytes/1024:g} KiB")
print(f"  pages in a {POOL}^2 pool                 = ({POOL}/{PAGE})^2 = {pages_in_pool}")
print(f"  pool total                               = {pool_bytes} B = {pool_bytes/1024**2:g} MiB")

texels = 100 * 10**6 * 10**4          # 100 km^2 -> m^2 -> cm^2, one texel per cm^2
print(f"  unique-texel warning: {texels:.0e} texels at {BPT} B = {texels/10**12:g} TB (decimal)")

print("ERROR -- feedback downscale not subtracted from the requested mip")
for s in (2, 4, 8):
    mips = s.bit_length() - 1                      # log2(s), exact for powers of two
    linear, areal = 1 / s, 1 / s**2
    print(f"  feedbackScale {s}: {mips} mips coarse, linear density {linear:.4%} of need, "
          f"areal {areal:.4%} -> {1-areal:.4%} low")

print("ERROR -- SampleGrad gradients not scaled into pool space")
ratio = (VIRT // POOL).bit_length() - 1            # log2(virtualSize/poolSize)
for page_mip in (0, 2, 4, 6):
    s_scale = VIRT / (POOL * 2**page_mip)
    print(f"  pageMip {page_mip}: s = {s_scale:g}, LOD error = pageMip - log2(virt/pool) = "
          f"{page_mip - ratio:+d} levels ({'too fine' if page_mip < ratio else 'too coarse' if page_mip > ratio else 'exact'})")
