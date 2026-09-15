import io, re
p = 'gaia/references/papers-generation.md'
s = io.open(p, encoding='utf-8').read()

# 1. front-matter description: name the new section
old_desc = "layered rock and grain classes, impact cratering, constraint-based authoring, and periodic construction."
new_desc = "layered rock and grain classes, impact cratering, constraint-based authoring, periodic construction, and clastic debris as scattered objects."
assert s.count(old_desc) == 1
s = s.replace(old_desc, new_desc)

# 2. the read-log census sentence
old_hdr = """Six sections were added to this file from documents written separately, and **three** of them
carry a read log below — impact cratering, constraint and sketch-based authoring, and periodicity
and boundaries."""
new_hdr = """Seven sections were added to this file from documents written separately, and **four** of them
carry a read log below — impact cratering, constraint and sketch-based authoring, periodicity
and boundaries, and clastic debris."""
assert s.count(old_hdr) == 1
s = s.replace(old_hdr, new_hdr)

# 3. read log for the new section, inserted before the attribution-corrections header
anchor = "## Attribution corrections that bind this family"
assert s.count(anchor) == 1
readlog = """### Clastic debris

**`bridson2007b`** — the author's own PDF at `cs.ubc.ca/~rbridson/docs/`, read in full; it is two
pages. §2 and §3 are quoted from that artefact. ⚠️ **That copy carries no article number, no DOI
and no page numbers** — only the title, the author and "ACM SIGGRAPH 2007 Sketches" — so the
locator cites sections and nothing else, and no article number is asserted below.

**`wentworth1922`** — **not obtained.** `journals.uchicago.edu` returned HTTP 403 to an
unauthenticated fetch and no author-side or repository copy was reached. The entry carries
`[not-opened]` and the size limits attached to it are stated on arithmetic this corpus can check
— the scale is geometric in φ = −log₂(d/mm), so its class edges fall on powers of two — not on
that paper's text. ⚠️ **The nearest openable secondary is corrupted**; see the entry.

"""
s = s.replace(anchor, readlog + anchor)

# 4. the new bibliography section, appended
section = """
## Clastic debris: size classes and scattering


- **bridson2007b** `P` — Bridson, R. (2007). *Fast Poisson Disk Sampling in Arbitrary Dimensions.* ACM SIGGRAPH 2007 Sketches. (The article number and DOI are not on the author's copy read here and are not asserted.) — The O(N) replacement for dart throwing, and the reason a scatter of rocks can be blue-noise without being slow. Three inputs: the domain extent in Rⁿ, **the minimum distance `r` between samples**, and a rejection limit `k`, "typically k=30". A background grid with cell size "bounded by r/sqrt(n), so that each grid cell will contain at most one sample" makes the neighbour test a fixed-size local scan, and the grid is then "a simple n-dimensional array of integers", −1 for empty. The loop keeps an active list; each iteration draws up to `k` candidates "uniformly from the spherical annulus between radius r and 2r around x_i" and either emits one or retires `x_i`. §3 gives the cost exactly: step 2 "is executed exactly 2N−1 times to produce N samples", each iteration O(k), so the algorithm is linear. ⚠️ **Its parameter is a separation, not a density.** One `r` fixes one spacing over the whole domain, so a single Bridson pass cannot express a boulder field and a pebble bed at once — that composition is `clastic-debris.md`'s problem, and this paper does not address it. ⚠️ **Not to be confused with `bridson2007`** in `## Noise` above, which is Bridson, Hourihan & Nordenstam's curl-noise paper of the same year; the two share a first author and nothing else.
- **wentworth1922** `P` [not-opened] — Wentworth, C.K. (1922). *A Scale of Grade and Class Terms for Clastic Sediments.* The Journal of Geology 30(5), 377–392. doi:10.1086/622910. — The origin of the grade scale every clast size in this skill is named against: boulder, cobble, pebble, granule, sand. **The artefact was not obtained** (see the read log), so nothing is quoted from it and no locator here claims a reading. What *is* asserted is arithmetic, and it is checkable without the paper: the scale is geometric with ratio 2, and Krumbein's φ = −log₂(d/mm) puts every class edge at an integer φ — φ = −8, −6, −2, −1 give **boulder > 256 mm, cobble 64–256, pebble 4–64, granule 2–4**. ⚠️ **The nearest openable secondary is corrupted, and was rejected.** "Exploring Our Fluid Earth" (Univ. of Hawaiʻi CRDG, 2014), Table 1.1, captioned "adapted from the Wentworth scale, Wentworth, C.K. (1922)", prints boulders as "250–100" — the range reversed and 250 for 256 — cobbles "65–250", pebbles "4–65", and coarse silt "0.031–0.625", the last off by a factor of ten. Rounding 64 to 65 and 256 to 250 destroys the one property that makes the scale usable, that a φ value converts to millimetres exactly. Recorded here because it is this corpus's most-feared defect class: a plausible number from a plausible source, wrong.
"""
s = s.rstrip('\n') + '\n' + section
io.open(p, 'w', encoding='utf-8').write(s)
print('ok')
