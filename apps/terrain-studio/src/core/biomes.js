// Biome presets — the climate half of "new terrain".
//
// Pure and DOM-free, like water-waves.js and hydrology.js, so an oracle can check every preset in
// plain node with no browser.
//
// WHY A PRESET AND NOT A SLIDER PER FIELD. A terrain's climate is seven numbers that are not
// independent: an arctic world at latitude 12 with a sea at 24 degrees is not a cold world, it is an
// incoherent one, and nothing in the app would stop you building it one slider at a time. Naming the
// combinations makes the coherent ones reachable in one click and leaves every field editable
// afterwards — the preset is a starting point, not a mode.
//
// EVERY NUMBER HERE IS PHYSICAL and stated in the unit the field already uses. Latitude in degrees,
// sea-surface temperature in degrees C, lapse rate in degC/km, wind in m/s and compass degrees,
// base elevation in metres, sea level as the Water node's 0..0.6 fraction, precipitation in mm/yr.
// Nothing is a magic 0..1 "amount".

export const BIOME_VERSION = 1

/**
 * The presets.
 *
 * `seaLevel` is the Water node's own parameter range (0..0.6 of the height range), not metres,
 * because that is the control it actually drives. Everything else is in real units.
 *
 * Lapse rate is not constant across climates and using 6.5 everywhere is a real error, not a
 * simplification: the environmental lapse rate runs near the dry adiabatic 9.8 degC/km over hot dry
 * ground where there is no condensation to release latent heat, and falls to roughly 5 in the humid
 * tropics where it does. A desert and a rainforest with the same lapse rate put their snowlines in
 * the wrong places.
 */
export const BIOMES = Object.freeze({
  temperate: Object.freeze({
    label: 'Temperate', latitude: 46, seaTemp: 12, lapseRate: 6.5, windDirection: 300, windSpeed: 10,
    baseElevation: 0, seaLevel: 0.30, precipMmYr: 900,
    note: 'Mid-latitude westerlies, moderate rainfall, seasonal snow on high ground.',
  }),
  tropical: Object.freeze({
    label: 'Tropical', latitude: 8, seaTemp: 28, lapseRate: 5.2, windDirection: 90, windSpeed: 7,
    baseElevation: 0, seaLevel: 0.32, precipMmYr: 2600,
    // Easterly trades, not westerlies: the low-latitude surface wind blows from the east.
    note: 'Easterly trades, very wet, snow only on the highest peaks.',
  }),
  arid: Object.freeze({
    label: 'Arid / Desert', latitude: 26, seaTemp: 22, lapseRate: 9.2, windDirection: 15, windSpeed: 13,
    baseElevation: 320, seaLevel: 0.06, precipMmYr: 90,
    // Near-dry-adiabatic: nothing condenses, so no latent heat is released on the way up.
    note: 'Subtropical high, steep lapse rate, almost no standing water.',
  }),
  mediterranean: Object.freeze({
    label: 'Mediterranean', latitude: 38, seaTemp: 19, lapseRate: 6.8, windDirection: 285, windSpeed: 9,
    baseElevation: 60, seaLevel: 0.28, precipMmYr: 550,
    note: 'Dry summers, wet winters, a coastline with real relief behind it.',
  }),
  boreal: Object.freeze({
    label: 'Boreal / Taiga', latitude: 60, seaTemp: 4, lapseRate: 5.8, windDirection: 260, windSpeed: 8,
    baseElevation: 180, seaLevel: 0.24, precipMmYr: 500,
    note: 'Cold and damp, long snow season, lakes everywhere.',
  }),
  alpine: Object.freeze({
    label: 'Alpine', latitude: 47, seaTemp: 6, lapseRate: 6.2, windDirection: 270, windSpeed: 14,
    baseElevation: 1400, seaLevel: 0.04, precipMmYr: 1400,
    // The one preset that raises the whole terrain: an alpine world is high ground, and starting it
    // at sea level would put its snowline off the top of the tile.
    note: 'High base elevation, strong wind, permanent snow and ice above the treeline.',
  }),
  polar: Object.freeze({
    label: 'Polar', latitude: 76, seaTemp: -1.5, lapseRate: 4.5, windDirection: 60, windSpeed: 12,
    baseElevation: 0, seaLevel: 0.26, precipMmYr: 250,
    // Sea water freezes near -1.8 degC, not 0: dissolved salt depresses the freezing point. A polar
    // preset with seaTemp 0 would render open water where there should be ice.
    note: 'Sea ice, a shallow lapse rate under a strong inversion, and very little precipitation.',
  }),
})

export const BIOME_KEYS = Object.freeze(Object.keys(BIOMES))
export const DEFAULT_BIOME = 'temperate'

/** The fields a biome writes into terrainDef. Named once so the oracle and the caller agree. */
export const TERRAIN_FIELDS = Object.freeze([
  'latitude', 'seaTemp', 'lapseRate', 'windDirection', 'windSpeed', 'baseElevation',
])

/**
 * The terrainDef overrides for a biome.
 *
 * Returns only the climate fields — never `scale`, `height`, `lattice` or `seed`. A biome is a
 * statement about weather, and letting it silently resize the world or re-roll the terrain would
 * make "change the biome" an unpredictable action.
 */
export function biomeTerrainOverrides(key) {
  const b = BIOMES[key] || BIOMES[DEFAULT_BIOME]
  const out = {}
  for (const f of TERRAIN_FIELDS) out[f] = b[f]
  return out
}

/** Sea level for the opening graph's Water node, in that node's own 0..0.6 parameter range. */
export function biomeSeaLevel(key) {
  const b = BIOMES[key] || BIOMES[DEFAULT_BIOME]
  return b.seaLevel
}

/** Annual precipitation in mm/yr, for the Physical Flow node's uniform fallback. */
export function biomePrecipMmYr(key) {
  const b = BIOMES[key] || BIOMES[DEFAULT_BIOME]
  return b.precipMmYr
}

/**
 * Surface temperature at an elevation, from the biome's sea-surface temperature and lapse rate.
 *
 * This is the relationship that makes a biome coherent rather than a bag of numbers: it is why the
 * polar preset has ice at sea level and the tropical one does not, and it is what the oracle checks
 * to prove the presets are ordered the way their names claim.
 */
export function temperatureAtM(key, elevationM) {
  const b = BIOMES[key] || BIOMES[DEFAULT_BIOME]
  return b.seaTemp - b.lapseRate * (elevationM / 1000)
}
