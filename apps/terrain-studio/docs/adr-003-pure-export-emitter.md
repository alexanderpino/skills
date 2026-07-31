# ADR 003 — Pure export requests and explicit emitters

**Status:** accepted
**Date:** 2026-07-31

## Context

The current `exportHeightmap()` in `src/legacy.js` normalizes the Output field, resamples hex to a
square raster, writes an 8-bit RGB canvas PNG, and clicks a download link. It discards physical range
and lives outside the graph. Chapter 08 requires R32F computation, quantization once at export,
physical manifest metadata, exact shared tile samples, and global evaluation before slicing. Chapter
14 requires node evaluation to remain pure.

## Decision drivers

- Export must be reproducible from the saved graph and selected profile.
- Preview/progressive evaluation must never trigger downloads or other side effects.
- Lossless physical masters and true 16-bit interchange are required before optional codecs.
- A package must be all-or-nothing and carry enough metadata to reconstruct physical values.
- Global hydrology and erosion must not change when output is tiled.

## Considered options

### A. Perform encoding/download in Export node evaluation

This gives a direct node metaphor but repeats side effects during preview, cache misses, and undo. It
breaks purity and cancellation and is rejected.

### B. Keep only the global export button

This avoids impure nodes but cannot name multiple products or profiles in the graph and cannot make
state/driver completeness reproducible. It is rejected.

### C. Declarative sink plus explicit executor — selected

An Export node returns an immutable request value. A user command discovers enabled requests,
evaluates dependencies, validates the complete package, encodes into staging memory, and invokes one
browser download only after all products succeed.

## Decision

### Request and execution boundary

`ExportRequest` contains source node/port identity, an authored product slug, format/options, profile
membership, and enabled state. Slugs are ASCII and unique within a profile. Node IDs remain provenance
and are not filenames. Evaluating, previewing, thumbnailing, undoing, or redoing produces zero emitter
calls.

The explicit executor orders requests by profile then slug, validates every request and the manifest,
encodes all bytes into staging, and exposes one package Blob only after success. Cancellation or any
failure discards staging and produces no download. Peak staging bytes and encoded product bytes are
reported and asserted. Every profile must author `maxStagingBytes`; there is no device-independent
default. The executor computes decoded working bytes, each encoder's worst-case output bytes,
manifest bytes, and deterministic container overhead, reports each term, and fails before allocation
when their sum exceeds the authored budget. This avoids calling chapter 08's 256 MiB 8k field size a
package ceiling when that field alone already consumes the entire amount.

### Formats and physical range

S6 ships these formats:

- little-endian IEEE-754 R32F raw;
- little-endian unsigned RAW/R16;
- true grayscale PNG16.

The typed package also supports `RG32F_LE`/`RGB32F_LE` vector rasters, `U32_LE` label rasters,
`JSON_SCALAR_V1`, and `JSON_FEATURES_V1`. Vector manifests declare ordered world-space components
(for example `eastMps`, `northMps`). Feature files contain stable feature IDs, kind, and world-metre
coordinates/attributes; they are not forced through raster posting metadata.

R16/PNG16 use one range per monolithic product. An authored profile range is used when present;
otherwise the monolithic observed finite min/max is recorded and used. A constant product records its
constant physical value and encodes all zeros, avoiding division by zero. Dequantization is exactly
`min + (u16 / 65535) * (max - min)`.

EXR is removed from Sprint 6. The repository has no selected browser codec or evidence-based bundle,
maintenance, or deterministic-encoding policy. R32F is the lossless production master. EXR may return
only through a later codec-selection ADR with measured candidate evidence; no partial encoder is
permitted.

The legacy 8-bit height download is removed from production export when PNG16 lands. It is not kept as
an alternate interchange path. Preview screenshots remain a separate visual feature and carry no
physical-height claim.

### Manifest and profiles

datum, product range/format/lens/dependencies, and epoch/drivers for continued state. A profile emits
The normative package schema is `docs/export-manifest.schema.json`. It discriminates scalar rasters,
vector rasters, labels, scalar values, and feature sets. It carries graph/substrate hash, root seed,
origin/extent, vertical datum, raster posting/layout where applicable, product declared/observed
ranges, format/lens/state role/dependencies, artifact path, and epoch/drivers for continued state.

JSON Schema validates structure. A separate package semantic validator rejects duplicate product
names, missing dependency/driver targets, unordered or out-of-declaration ranges, posting/cell-size
inconsistency (`extent/(N-1)` for vertex, `extent/N` for pixel), unsafe/absolute/traversing artifact
paths, mismatched vector component counts, constant products without equal observed endpoints, and
continued state without `stateRole: initial`, epoch, and non-empty drivers. A profile emits exactly
its declared products; undeclared products are errors.

`exportPolicy` is one of `raw`, `previewOnly`, or `classification`. Production profiles accept only
raw physical products. A missing policy is a registration error. This implements chapters 08/27 and
the Masking Doctrine without a hard-coded node-name blacklist.

### Tiling

Every requested field is evaluated over the monolithic domain first. Hex-to-square interchange is
also performed once on the monolithic field. Vertex-posted height tiles duplicate the exact shared
sample and use core stride `tileSamples - 1`; pixel-posted maps use non-overlapping texel extents.
Aprons are copied from the monolithic result, never recomputed per tile.

Apron width is product-specific:

- raw fields: zero unless the consumer profile requires overlap;
- first derivatives such as normals: one source sample;
- finite neighbourhood products: the descriptor's declared support radius;
- GLOBAL products: compute monolithically, then slice the completed result.

There is no blanket one-cell rule for all derivatives.

### Bake closure

Bake validation operates on `(node, outputPort)`. Baking a product requires every transitive source
port it depends on to be baked. Continued-state products additionally require their declared drivers
and a non-empty authored epoch in the same package. Violations name the first offending source and
destination ports and stop before encoding.

## Consequences and gates

- Repeated graph evaluation produces zero emitter calls; one explicit command invokes each enabled
  request once in stable order.
- The exact decoded-plus-worst-case-encoded-plus-manifest/container staging estimate is at most the
  profile's required `maxStagingBytes`; an over-budget fixture fails before allocating/downloading.
- R32F round-trips source Float32 bytes exactly with explicit endian/shape metadata.
- PNG IHDR reports 16-bit grayscale. For physical range `R=max-min`, quantization error before
  Float32 storage is at most `R/(2*65535)`; the test computes the additional Float32 rounding bound
  with `nextUp(expected)-expected` at the tested magnitude rather than saying only “float epsilon.”
- RAW/R16 and PNG16 dequantize through the same formula and range.
- Stitched tile cores reproduce the monolithic product within the selected format's analytic bound;
  shared vertex samples are bit-identical.
- Per-tile scheduling of a GLOBAL node is rejected before evaluation.
- The L4 profile schema validates offline. EXR absence is explicit and does not block S6.

The trade-off is staging memory and no EXR in the first production emitter. In return, graph purity,
physical reconstruction, cancellation, and tile science become testable contracts.
