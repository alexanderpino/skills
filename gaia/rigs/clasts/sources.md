# Verified sources for the clastic-debris document
Extracted from the artefacts themselves, not paraphrased. Locators are quotable.

## bridson2007 — tier P — OPENED, text extracted from the author's own PDF
Robert Bridson, "Fast Poisson Disk Sampling in Arbitrary Dimensions", ACM SIGGRAPH 2007 Sketches.
https://www.cs.ubc.ca/~rbridson/docs/bridson-siggraph07-poissondisk.pdf

VERBATIM, §2 The Algorithm:
- inputs: "the extent of the sample domain in R^n, the minimum distance r between samples, and a
  constant k as the limit of samples to choose before rejection in the algorithm (typically k=30)"
- Step 0: "We pick the cell size to be bounded by r/sqrt(n), so that each grid cell will contain at
  most one sample, and thus the grid can be implemented as a simple n-dimensional array of integers:
  the default -1 indicates no sample, a non-negative integer gives the index of the sample located
  in a cell."
- Step 1: "Select the initial sample, x0, randomly chosen uniformly from the domain. Insert it into
  the background grid, and initialize the active list (an array of sample indices) with this index."
- Step 2: "While the active list is not empty, choose a random index from it (say i). Generate up to
  k points chosen uniformly from the spherical annulus between radius r and 2r around x_i. For each
  point in turn, check if it is within distance r of existing samples (using the background grid to
  only test nearby samples). If a point is adequately far from existing samples, emit it as the next
  sample and add it to the active list. If after k attempts no such point is found, instead remove i
  from the active list."

VERBATIM, §3 Analysis:
- "Step 2 is executed exactly 2N-1 times to produce N samples: each iteration either produces a new
  sample and adds it to the active list, or removes an existing sample from the active list."
- "Each iteration of step 2 takes O(k) time, and since k is held constant (typically quite small)
  the algorithm is linear."

Prior art it builds on, both real and cited in its own References:
- COOK, R.L. 1986. Stochastic sampling in computer graphics. ACM Trans. Graph. 5, 1.
- DUNBAR, D., AND HUMPHREYS, G. 2006. A spatial data structure for fast poisson-disk sample
  generation. ACM Trans. Graph. 25, 3, 503-508.

NOTE FOR THE WRITE-UP: r is a MINIMUM SEPARATION, not a density. A single r cannot express a
boulder field and a pebble bed at once, which is exactly the problem a clast document has to solve.

## wentworth1922 — tier P — [not-opened]: paywalled, HTTP 403
Wentworth, C.K. (1922). "A Scale of Grade and Class Terms for Clastic Sediments."
The Journal of Geology 30(5): 377-392.  https://doi.org/10.1086/622910 / JSTOR 30063207
journals.uchicago.edu returned HTTP 403 to an unauthenticated fetch. The primary was NOT opened
here and the entry must carry [not-opened]; the size limits below are stated on the
INDEPENDENTLY CHECKABLE ground that the scale is geometric with ratio 2, not on that paper's text.

Class edges, from phi = -log2(d in mm) at integer phi — arithmetic verified here:
  boulder / cobble   phi = -8   d = 256 mm
  cobble  / pebble   phi = -6   d =  64 mm
  pebble  / granule  phi = -2   d =   4 mm
  granule / sand     phi = -1   d =   2 mm
So: BOULDER > 256 mm, COBBLE 64-256, PEBBLE 4-64, GRANULE 2-4.

## FINDING — a secondary source that carries the numbers WRONG. Do not use it.
"Exploring Our Fluid Earth" (Univ. of Hawaii CRDG, 2014), Table 1.1, which explicitly says
"Table adapted from the Wentworth scale, Wentworth, C.K. (1922)":
  prints "Boulder 250-100"  -- range REVERSED, and 250 for 256
  prints "Cobbles 65-250"   -- 65 for 64, 250 for 256
  prints "Pebbles 4-65"     -- 65 for 64
  prints "Coarse silt 0.031-0.625" -- 0.625 for 0.0625, off by a factor of ten
Rounding 64 to 65 and 256 to 250 destroys the one property that makes the scale usable: every
edge is a power of two, so a phi value converts to millimetres exactly. Recorded because it is the
defect class this corpus most fears -- a plausible number from a plausible source, wrong.
