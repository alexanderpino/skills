# ADR 005 — Physical fields, climate resolution, and legacy migration

**Status:** accepted
**Date:** 2026-07-31

## Context

Terrain Studio's legacy graph values are dimensionless scalar rasters. The viewport and
`metricHeightField` autolevel the current field range onto `[baseElevation, baseElevation + height]`;
Output may normalize again. S3-S7 require metre-valued height/layer fields, `mm/yr` precipitation,
`m3/s` discharge, continued Snow state, and lithology-dependent Stream Power. Relabelling the legacy
array as metres would silently corrupt every volume and rate calculation.

Chapter 03 supplies authored discharge sources in `m3/s`; chapter 13 supplies absolute precipitation
in `mm/yr` and recommends 500–1000 m climate cells; chapter 04 defines
`dh/dt = U - K*A^m*S^n`; chapter 27 requires Snow initial state plus authored drivers/epoch. The
corpus does not provide a unique inverse conversion from Terrain Studio's legacy settled snowfall
slider to annual precipitation, density, or epoch.

## Decision drivers

- Preserve existing document output byte-for-byte through migration.
- Make every new physical field and conversion dimensionally explicit.
- Avoid fabricating Snow density, epoch, climate supply, or weathering history.
- Keep climate-grid selection deterministic and cacheable.
- Let lithology vary erodibility without a port whose SI dimension changes when `m` changes.

## Considered options

### Height migration

1. Relabel legacy samples as metres: rejected because current samples are normalized and autolevelled.
2. Convert every legacy node to metres at once: physically clean but breaks every digest and exceeds
   the typed-DAG migration blast radius.
3. Versioned boundary adapter — selected. Legacy nodes remain `heightNormalized`; physical nodes
   consume `heightM` through an explicit frame adapter.

### Snow migration

1. Infer annual moisture and density from `snowfall:m`: rejected because the inverse is not unique.
2. Pick default density and epoch: rejected as fabricated state.
3. Preserve `Snow/1` compatibility and require explicit upgrade to `Snow/2` — selected.

### Lithology coupling

1. Emit absolute `K`: its SI dimension changes with authored area exponent `m`.
2. Emit normalized hardness then invert: ambiguous and not the chapter-11 contract.
3. Emit dimensionless positive erodibility factor multiplied by the node's physical base `K0` —
   selected.

## Decision

### Height frame

Legacy scalar terrain remains semantic type `heightNormalized`, finite but not necessarily confined to
`[0,1]`. The compatibility conversion to absolute elevation is the measured viewport frame:

```text
heightM[i] = baseElevationM
           + (legacy[i] - fieldMin) / (fieldMax - fieldMin) * reliefHeightM
```

A constant field maps to `baseElevationM`; this explicit policy replaces the current hidden
`range || 1` behavior. The adapter records `fieldMin`, `fieldMax`, `baseElevationM`, and
`reliefHeightM` in value metadata/cache identity. The inverse is
`legacy = fieldMin + ((heightM-baseElevationM)/reliefHeightM)*(fieldMax-fieldMin)` and is permitted
only for a legacy consumer using the same frame metadata. New physical nodes never normalize.
Normalization remains an explicit preview/legacy Output adapter, not a physical field operation.

S3's stack is absolute `bedrockHeightM + soilDepthM + sedimentDepthM + sandDepthM`. A fixture that
uses no sand must assert `sandDepthM == 0`; the identity never omits the term.

### Precipitation and discharge

A climatological year is exactly 365 days = 31,536,000 seconds for this contract. At each raster cell:

```text
qRainCellM3S = precipitationMmYr * 1e-3 * cellAreaM2 / 31_536_000
QoutletM3S   = sum(qRainCellM3S over contributing cells) + sum(authoredSourceM3S)
```

The year convention and conversion occur once at the Physical Flow boundary. Precipitation remains
`mm/yr` everywhere upstream; authored point/boundary sources remain `m3/s`.

### Climate grid

`climateCellSizeM` is a serialized parameter in the chapter-13 inclusive range 500–1000 m. Its
accepted initial value is 1000 m: the coarsest cited sufficient sampling, selected to minimize work
without claiming extra spatial information. It participates in parameter serialization and cache
identity. The internal grid covers the whole world region with `ceil(extent/climateCellSizeM)` cells
per axis and records the actual resulting pitch; resampling back to the terrain uses world-space
coordinates.

### Snow versions and SWE

Unversioned legacy Snow migrates to `Snow/1`, which preserves the existing evaluator and settled-depth
parameters exactly. It is preview-compatible but has `exportPolicy: previewOnly`; it cannot satisfy
the Snow Rule or continued-state export.

`Snow/2` requires:

- `moistureMmSWEYr` (`mm SWE/yr`);
- `accumulationDays` (`day`, positive; initial value 365 by the one-year input convention);
- `densityRatio = rhoSnow/rhoWater` (`ratio`, finite and `>0`), authored with no default;
- `meltFactorMmSWEPerCDay` (`mm SWE/(degC*day)`, finite and non-negative), authored;
- `epoch` (date-time), authored;
- temperature, insolation, and wind drivers.

For a cell:

```text
supplySWE_M = moistureMmSWEYr * 1e-3 * accumulationDays / 365 * freezeFraction
meltSWE_M   = meltFactorMmSWEPerCDay * 1e-3
              * max(temperatureC, 0) * insolation * accumulationDays
snowWaterEquivalentM = max(0, initialSWE_M + supplySWE_M - meltSWE_M)
snowDepthM = snowWaterEquivalentM / densityRatio
```

`initialSnowDepthM` may be carried from authoring only when the author supplies the corresponding
`initialSWE_M` or density ratio. No migration invents that relationship. `Snow/2` exports depth, SWE,
provenance, meltwater, drivers, and epoch.

The existing `adhesion` parameter remains an authored compatibility control for the measured holding-
depth family; its current 0.6 m value is preserved only in `Snow/1`. `Snow/2` requires an authored
holding depth and labels it as an F-tier look control, not a physical constant.

### Stream Power and lithology

The physical v2 node uses chapter 04 with drainage area:

```text
dh/dt = U - K0 * erodibilityFactor * A^m * S^n + D*laplacian(h)
```

`A` is `m2`, `S` is dimensionless, `U` is `m/yr`, and `n=1` for the Braun-Willett closed form. The
area exponent remains authored in `[0.2,0.8]`. Therefore `K0` has unit
`m^(1-2m)/yr`, represented as a node parameter whose descriptor is validated together with `m`, while
`strataErodibilityFactor` is a positive dimensionless ratio. The bed table emits that ratio directly;
low factors are resistant and high factors erode faster. This avoids pretending one fixed SI unit can
serve every value of `m`.

The legacy Stream Power node remains version 1 with calibrated dimensionless `Kdt`; it cannot consume
the physical lithology port. S7 couples lithology to Stream Power/2 only.

## Consequences and gates

- A frozen legacy graph remains byte-identical because legacy nodes and Snow/1 retain their evaluators.
- A type checker rejects `heightNormalized` where `heightM` is required unless the explicit frame
  adapter is present.
- Round-tripping a non-constant legacy field through the same frame metadata reproduces each sample
  within the Float32 forward-error bound; constant-field policy is explicitly tested.
- Uniform precipitation over an analytic domain produces the equation above within the Float32
  reduction bound; a missing `1e-3` or `31_536_000` factor is an armed mutation.
- Changing `climateCellSizeM` changes the cache key. The initial 1000 m policy produces no grid finer
  than the corpus claims useful.
- Snow/1 export fails. Snow/2 registration/export fails without density ratio, SWE melt factor, epoch,
  or drivers. Two authored density ratios and accumulation intervals match the analytic equations.
- Under identical forcing, a lower erodibility factor incises less. Connecting the factor to legacy
  Stream Power/1 is a type/version error.

The cost is a visible compatibility boundary and versioned Snow/Stream Power nodes. The benefit is
that migration remains honest while every new physical equation has coherent units.
