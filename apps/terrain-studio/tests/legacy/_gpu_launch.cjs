// Shared browser launch profiles for the oracle suite.
//
// WHY THIS FILE EXISTS
//
// 77 of the 78 oracles launch Chrome with
//
//   --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader
//
// which is correct for them: they verify CPU kernels and WebGL2 rendering, and SwiftShader makes
// that deterministic and machine-independent. It is also, measured on this machine, fatal to
// WebGPU — `navigator.gpu` still exists, so a naive probe reports "WebGPU available", but
// `requestAdapter()` resolves to **null** and no device is ever obtained:
//
//   headless-default        adapter=true  device=true  maxTextureDimension2D=16384  intel/xe-lpg
//   headless-swiftshader    adapter=false                       <-- no adapter at all
//   headless-unsafe-webgpu  adapter=true  device=true  maxTextureDimension2D=16384  intel/xe-lpg
//   headed-default          adapter=true  device=true  maxTextureDimension2D=16384  intel/xe-lpg
//
// So every Sprint 10 gate written to the house pattern would have failed, or worse skipped
// vacuously, for a reason that has nothing to do with the code under test. Sprint 10 is the
// cook-free WebGPU heightfield: its gates are the whole point of the sprint.
//
// The second trap is the origin. WebGPU is a secure-context API, so `navigator.gpu` is undefined
// on `file://` and on `about:blank`. The suite's own default URL is a `file://` path
// (`process.env.STUDIO_URL || 'file://' + ...`), which means a WebGPU oracle run without a served
// origin reports "no WebGPU" on a machine that has it. Measured:
//
//   about:blank             hasGpu=false secure=false
//   http://localhost:<port> hasGpu=true  secure=true
//
// GPU oracles therefore MUST run over the served origin (STUDIO_URL), never the file:// fallback.
'use strict'

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')

// The house profile. Deterministic software rendering; no WebGPU adapter.
const SWIFTSHADER_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox']

// The GPU profile. Real adapter, so WebGPU can actually be exercised.
const GPU_ARGS = ['--no-sandbox']

/**
 * Launch Chrome with the real GPU adapter available (WebGPU usable).
 * `variant: 'swiftshader'` deliberately reproduces the house profile so an oracle can arm a
 * control that proves it is measuring the adapter rather than restating a constant.
 */
async function launchForGpu(chromium, { variant = 'gpu', headless = true } = {}) {
  const args = variant === 'swiftshader' ? SWIFTSHADER_ARGS : GPU_ARGS
  return chromium.launch({ headless, executablePath: EXE, args })
}

/**
 * A GPU oracle must run against a served origin. Returns the URL or throws — an oracle that
 * silently probed file:// would report "no WebGPU" as though it were a product fact.
 */
function requireServedUrl() {
  const url = process.env.STUDIO_URL
  if (!url || !/^https?:\/\//.test(url)) {
    throw new Error(
      'GPU oracles require a served origin: WebGPU is a secure-context API and navigator.gpu is '
      + 'undefined on file://. Run through scripts/run-legacy-verify.mjs, which sets STUDIO_URL. '
      + `Got STUDIO_URL=${JSON.stringify(url || null)}`
    )
  }
  return url
}

// ExtremeCapability/1, verbatim from docs/adr-008-cook-free-webgpu-heightfield.md:233-240.
// These are the WebGPU specification's guaranteed default limits. They are minima the algorithms
// partition work to, never raised to accommodate an oversized design.
const EXTREME_REQUIRED_LIMITS = {
  maxTextureDimension2D: 8192,
  maxBufferSize: 268435456,
  maxStorageBufferBindingSize: 134217728,
  maxComputeWorkgroupsPerDimension: 65535,
  maxComputeInvocationsPerWorkgroup: 256,
  maxStorageBuffersPerShaderStage: 8,
}

module.exports = { EXE, SWIFTSHADER_ARGS, GPU_ARGS, launchForGpu, requireServedUrl, EXTREME_REQUIRED_LIMITS }
