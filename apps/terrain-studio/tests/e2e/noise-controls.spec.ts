/**
 * Noise parameters span ratios, so their authoring precision should be multiplicative:
 * equal track distances produce equal value ratios. Warp strength also needs a true off
 * position followed by fine control over subtle non-zero displacement.
 */
import { test, expect } from './fixtures'

type SampledControl = {
  scale: unknown
  floor: number
  max: number
  def: number
  zero: boolean
  defaultTrack: number
  ticks: string[]
  samples: number[]
}

test.describe('@correctness noise controls', () => {
  test('frequency, density, and subtle warp strength use logarithmic tracks', async ({ studio: page }) => {
    const controls = await page.evaluate(() => {
      const savedSelected = selected
      let id = -10_000

      const sample = (type: string, key: string, positions: number[]): SampledControl => {
        const descriptor = TYPES[type].params.find((param) => param.key === key)!
        selected = { id: id--, type, params: { [key]: descriptor.def } }
        const field = buildField(descriptor)
        const input = field.querySelector<HTMLInputElement>('input[type="range"]')!
        const defaultTrack = +input.value
        const samples = positions.map((position) => {
          input.value = String(position)
          input.dispatchEvent(new Event('input', { bubbles: true }))
          return Number(selected!.params[key])
        })
        return {
          scale: descriptor.scale,
          floor: descriptor.floor,
          max: descriptor.max,
          def: descriptor.def,
          zero: descriptor.zero,
          defaultTrack,
          ticks: [...field.querySelectorAll<HTMLElement>('.logticks span')].map((tick) => tick.textContent ?? ''),
          samples,
        }
      }

      const result = {
        perlin: sample('perlin', 'freq', [0, 0.25, 0.5, 0.75, 1]),
        simplex: sample('simplex', 'freq', [0, 0.5, 1]),
        ridged: sample('ridged', 'freq', [0, 0.5, 1]),
        worley: sample('worley', 'freq', [0, 0.5, 1]),
        warpFrequency: sample('warp', 'freq', [0, 0.5, 1]),
        warpStrength: sample('warp', 'strength', [0, 0.0025, 0.25, 0.5, 0.75, 1]),
      }
      selected = savedSelected
      return result
    })

    const frequencyControls = [
      controls.perlin,
      controls.simplex,
      controls.ridged,
      controls.worley,
      controls.warpFrequency,
    ]
    for (const control of frequencyControls) {
      expect(control.scale).toBe('log')
      expect(control.zero).toBe(false)
      expect(control.samples[0]).toBeCloseTo(control.floor, 10)
      expect(control.samples.at(-1)).toBeCloseTo(control.max, 10)
      expect(control.ticks.length).toBeGreaterThan(0)
    }

    // Equal track intervals have a constant ratio, which distinguishes the control from a
    // merely relabelled linear range.
    const perlinRatios = controls.perlin.samples.slice(1).map((value, i) => value / controls.perlin.samples[i])
    perlinRatios.forEach((ratio) => expect(ratio).toBeCloseTo(perlinRatios[0], 10))

    expect(controls.perlin).toMatchObject({ floor: 0.5, max: 12, def: 3 })
    expect(controls.simplex).toMatchObject({ floor: 0.5, max: 12, def: 3 })
    expect(controls.ridged).toMatchObject({ floor: 0.5, max: 12, def: 3.5 })
    expect(controls.worley).toMatchObject({ floor: 2, max: 16, def: 6 })
    expect(controls.warpFrequency).toMatchObject({ floor: 0.5, max: 8, def: 3 })

    const warp = controls.warpStrength
    expect(warp).toMatchObject({ scale: 'log', floor: 0.001, max: 0.4, def: 0.12, zero: true })
    expect(warp.samples[0]).toBe(0)
    expect(warp.samples[1]).toBeGreaterThanOrEqual(0.001)
    expect(warp.samples[1]).toBeLessThan(0.0011)
    expect(warp.samples[3]).toBeCloseTo(0.02, 10)
    expect(warp.samples.at(-1)).toBeCloseTo(0.4, 10)

    // Existing graph documents store real values, so all shipped defaults must map back to their
    // exact logarithmic track position without changing the serialized parameter contract.
    for (const control of Object.values(controls)) {
      const expected = Math.log(control.def / control.floor) / Math.log(control.max / control.floor)
      expect(Math.abs(control.defaultTrack - expected)).toBeLessThanOrEqual(0.00125 + Number.EPSILON)
    }
  })
})
