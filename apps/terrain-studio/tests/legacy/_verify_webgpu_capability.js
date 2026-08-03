// ExtremeCapability/1 harness probe — docs/adr-008-cook-free-webgpu-heightfield.md:228-246.
//
// This is NOT S10.1. S10.1 owns the product behaviour: capability tiers, the blocking startup
// modal, "No supported graphics capability", persisted-preference-cannot-bypass-a-fresh-probe.
// This oracle owns the question that has to be answered before any of that can be gated at all:
// **can the verification harness reach a real WebGPU device?**
//
// It exists because the answer was silently "no". The suite's house launch profile uses
// SwiftShader, under which navigator.gpu still exists but requestAdapter() resolves to null. A
// Sprint 10 gate written to the house pattern would report "no WebGPU here" forever, on a machine
// that has WebGPU, and that reading would look exactly like a product fact.
//
// Two armed controls, because there are two independent ways to get a false negative:
//   --mutate=swiftshader-launch-flags   house profile          -> adapter null   -> RED
//   --mutate=insecure-origin            about:blank            -> no navigator.gpu -> RED
const { chromium } = require('playwright-core')
const { launchForGpu, requireServedUrl, EXTREME_REQUIRED_LIMITS } = require('./_gpu_launch.cjs')

const mutation = (process.argv.find(value => value.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = ['swiftshader-launch-flags', 'insecure-origin']
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

const assertions = []
const check = (name, condition, detail) => { assertions.push({ name, ok: !!condition, detail }); return !!condition }

;(async () => {
  const url = requireServedUrl()
  const browser = await launchForGpu(chromium, {
    variant: mutation === 'swiftshader-launch-flags' ? 'swiftshader' : 'gpu',
  })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  // The isolated runner serves source by wrapping vite.middlewares in a plain http server, so the
  // dev client's websocket has nothing to attach to and reports "WebSocket closed without opened."
  // That is dev-server transport, cannot occur in a production build (no @vite/client is emitted),
  // and is timing-dependent — which makes it a latent flake for every oracle that asserts on page
  // errors, not just this one. Excluded by exact text only, and the excluded set is reported, so a
  // real error can never hide behind the filter.
  const HARNESS_TRANSPORT_NOISE = ['WebSocket closed without opened.']
  const errors = []
  const filtered = []
  page.on('pageerror', error => {
    (HARNESS_TRANSPORT_NOISE.includes(error.message) ? filtered : errors).push(error.message)
  })

  // The insecure-origin control never reaches the served page: about:blank is not a secure
  // context, so navigator.gpu is undefined there regardless of the adapter.
  await page.goto(mutation === 'insecure-origin' ? 'about:blank' : url, { waitUntil: 'load' })
  // Settle like the rest of the suite, so the probe measures a booted page rather than one still
  // executing its module graph.
  if (mutation !== 'insecure-origin') await page.waitForTimeout(1200)

  const probe = await page.evaluate(async limits => {
    const out = { secureContext: isSecureContext, hasGpu: typeof navigator.gpu !== 'undefined' }
    if (!out.hasGpu) return out
    try {
      const adapter = await navigator.gpu.requestAdapter()
      out.adapter = adapter !== null
      if (!adapter) return out
      out.adapterInfo = adapter.info ? `${adapter.info.vendor}/${adapter.info.architecture}` : null
      out.adapterLimits = {}
      for (const key of Object.keys(limits)) out.adapterLimits[key] = adapter.limits[key]

      // Request EXACTLY the guaranteed defaults and no optional feature, per the ADR. Asking for
      // more would prove the machine is generous, not that the profile is satisfiable.
      const device = await adapter.requestDevice({ requiredFeatures: [], requiredLimits: limits })
      out.device = !!device
      if (!device) return out

      // Validation smoke: the three format usages the runtime actually depends on.
      const lost = []
      device.pushErrorScope('validation')
      const height = device.createTexture({
        size: [256, 256], format: 'r32float',
        usage: GPUTextureUsage.COPY_DST | GPUTextureUsage.TEXTURE_BINDING,
      })
      const depth = device.createTexture({
        size: [256, 256], format: 'depth24plus', usage: GPUTextureUsage.RENDER_ATTACHMENT,
      })
      const canvasFormat = navigator.gpu.getPreferredCanvasFormat()
      const colour = device.createTexture({
        size: [256, 256], format: canvasFormat, usage: GPUTextureUsage.RENDER_ATTACHMENT,
      })
      const validationError = await device.popErrorScope()
      height.destroy(); depth.destroy(); colour.destroy()
      out.canvasFormat = canvasFormat
      out.validationError = validationError ? validationError.message : null
      out.formatsOk = !validationError && lost.length === 0
      return out
    } catch (error) { out.error = String(error).slice(0, 200); return out }
  }, EXTREME_REQUIRED_LIMITS)

  check('secure context', probe.secureContext === true, probe.secureContext)
  check('navigator.gpu exists', probe.hasGpu === true, probe.hasGpu)
  check('requestAdapter non-null', probe.adapter === true, probe.adapter)
  check('requestDevice non-null', probe.device === true, probe.device)
  check('r32float / depth24plus / preferred-canvas usages validate', probe.formatsOk === true, probe.validationError)
  for (const [key, required] of Object.entries(EXTREME_REQUIRED_LIMITS)) {
    const actual = probe.adapterLimits ? probe.adapterLimits[key] : undefined
    check(`limit ${key} >= ${required}`, typeof actual === 'number' && actual >= required, actual)
  }
  check('no page errors', errors.length === 0, errors)

  // Absence of evidence is a failure: a probe that compared nothing is red, not green.
  const counted = assertions.length
  check('assertion inventory non-empty', counted >= 11, counted)

  let ok = assertions.every(a => a.ok)
  if (mutation) {
    // A mutated run that still reports ok means this oracle is not measuring the adapter.
    if (ok) { console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`) }
    ok = false
  }

  const failed = assertions.filter(a => !a.ok).map(a => a.name)
  console.log(`${ok ? 'PASS' : 'FAIL'}  webgpu capability adapter=${probe.adapter === true} device=${probe.device === true} `
    + `info=${probe.adapterInfo || 'n/a'} maxTex2D=${probe.adapterLimits ? probe.adapterLimits.maxTextureDimension2D : 'n/a'} `
    + `assertions=${counted} failed=${failed.length} filtered=${filtered.length} mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ mutation, probe, assertions, filteredHarnessNoise: filtered, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
