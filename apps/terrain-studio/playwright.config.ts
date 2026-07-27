import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))

// PHASE 2 — the real test runner arrives alongside the ad-hoc _verify_*.js scripts, it does not
// replace them yet. Both suites run against the SAME document: vite's `root` points at
// terrain-architect/studio, so a spec here and a legacy script there load byte-identical bytes.
const PORT = 5173
const BASE_URL = `http://127.0.0.1:${PORT}`

// Software GL backend selection. These four flags are quoted, verbatim, by every timing number in
// terrain-architect/studio/README.md and by the 50 legacy verification scripts. SwiftShader is
// deterministic where a real GPU is not, so the numbers are comparable across machines and across
// CI — but ONLY while the flags stay identical. Changing, reordering for "tidiness", or dropping one
// silently invalidates every recorded measurement in this repo. Do not touch them without also
// re-measuring the README.
const SWIFTSHADER_ARGS = [
  '--use-gl=angle',
  '--use-angle=swiftshader',
  '--enable-unsafe-swiftshader',
  '--no-sandbox',
]

export default defineConfig({
  testDir: resolve(here, 'tests/e2e'),
  outputDir: resolve(here, 'test-results'),

  // A single SwiftShader WebGL context already saturates several cores. Two of them do not run
  // twice as fast — they contend for the same CPU rasteriser, and the wall-clock numbers the
  // @timing specs record become a measurement of scheduler luck rather than of the terrain code.
  // So: one worker, no intra-file parallelism. This is a deliberate, paid-for cost.
  //
  // The escape hatch is the tag: @correctness specs assert DOM/graph state and are safe to
  // parallelise; @timing specs assert wall-clock or frame behaviour and are not. A future change
  // can run `--grep @correctness` with fullyParallel and leave `--grep @timing` serialised.
  fullyParallel: false,
  workers: 1,

  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,

  // SwiftShader rasterises 512² terrain fields on the CPU; the legacy scripts budget 1.2–2.6 s of
  // boot alone. 30 s (the default) is not enough headroom on a cold cache.
  timeout: 120_000,
  expect: { timeout: 20_000 },

  reporter: process.env.CI
    ? [
        ['github'],
        ['list'],
        ['html', { outputFolder: resolve(here, 'playwright-report'), open: 'never' }],
      ]
    : [
        ['list'],
        ['html', { outputFolder: resolve(here, 'playwright-report'), open: 'never' }],
      ],

  use: {
    baseURL: BASE_URL,
    // Matches the legacy scripts' newPage({viewport:{width:1440,height:900}}) exactly. The menubar
    // and toolbar specs assert desktop-vs-compact breakpoints off this width.
    viewport: { width: 1440, height: 900 },
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium-swiftshader',
      use: {
        // Playwright-MANAGED chromium, deliberately: the legacy scripts hardcode
        // C:\Program Files\Google\Chrome\... (42 of them) or Edge (8 of them), so the suite has
        // silently been running on two different engines at two uncontrolled versions. A pinned,
        // downloaded browser is the only way the numbers mean the same thing twice.
        browserName: 'chromium',
        launchOptions: { args: SWIFTSHADER_ARGS },
      },
    },
  ],

  // Playwright owns the dev server. `reuseExistingServer` locally so an already-open `npm run dev`
  // is picked up instead of fighting over the strict port; never in CI, where a stale server would
  // silently serve stale bytes.
  webServer: {
    command: `npx vite --port ${PORT} --strictPort`,
    cwd: here,
    url: `${BASE_URL}/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
})
