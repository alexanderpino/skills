import { test as base, expect, type Page, type TestInfo } from '@playwright/test'

/* ---------------------------------------------------------------- readiness ---
 *
 * The app is one classic <script> that ends in `boot()`. boot() is fully synchronous:
 *
 *     resizeGraph(); initGL(); defaultGraph(); evalGraph(); historyReady=true; ...
 *
 * and evalGraph() -> finishGraphEvaluation() is the ONLY thing that writes
 * `Graph evaluated · N nodes` into #statMsg and a non-zero node count into #statNodes
 * (both start as literal "Ready" / "0" in the shipped markup).
 *
 * The legacy scripts approximate all of that with waitForTimeout(1100–2600) — a number that is
 * simultaneously too long on a warm machine and too short on a cold one. We wait on the state
 * itself instead, and on three independent facts so that a partial boot cannot pass:
 *
 *   1. `historyReady === true`  — boot() reached its last statement. This is a top-level `let`, so
 *      it is a global LEXICAL binding, not a window property; a bare reference resolves it, which
 *      is exactly how every legacy script already reads `nodes`, `edges`, `cam`, `RES`, …
 *   2. #statNodes parses to a positive integer — a graph was built AND rendered into the status bar.
 *   3. #statMsg matches /^Graph evaluated · \d+ nodes$/ — finishGraphEvaluation() ran with an
 *      output node present (it writes "Add an Output node" otherwise, so this also rules out the
 *      degenerate empty-graph success).
 *
 * Then two animation frames. renderGL() re-schedules itself via requestAnimationFrame, so getting
 * two frames back proves the render loop is actually turning rather than merely scheduled — and it
 * also flushes the `setTimeout(…, 0)` GPU-capability probe that runs just after boot and can
 * disable #gpuBtn. Polling is 'raf'-driven for the same reason.
 *
 * The timeout is a generous backstop, not the mechanism: on a healthy machine this resolves in a
 * few hundred milliseconds, well under the fixed sleeps it replaces.
 */
export const BOOT_TIMEOUT = 45_000

export async function settle(page: Page): Promise<void> {
  await page.evaluate(
    () => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))),
  )
}

export async function waitForStudioBoot(page: Page, timeout = BOOT_TIMEOUT): Promise<void> {
  await page.waitForFunction(
    () => {
      let bootReturned = false
      // `historyReady` may legitimately not exist yet (script not parsed / temporal dead zone),
      // and a throwing predicate would fail the wait rather than retry it.
      try {
        bootReturned = historyReady === true
      } catch {
        bootReturned = false
      }
      const count = Number(document.querySelector('#statNodes')?.textContent?.trim())
      const msg = document.querySelector('#statMsg')?.textContent?.trim() ?? ''
      return bootReturned && Number.isFinite(count) && count > 0 && /^Graph evaluated · \d+ nodes$/.test(msg)
    },
    undefined,
    { timeout, polling: 'raf' },
  )
  await settle(page)
}

/** Screenshot as a test attachment rather than a stray _shot_*.png in the skill tree. */
export async function attachShot(page: Page, testInfo: TestInfo, name: string): Promise<void> {
  await testInfo.attach(name, { body: await page.screenshot(), contentType: 'image/png' })
}

/* ---------------------------------------------------------------- fixtures --- */

type StudioFixtures = {
  /**
   * Opt out of the "no console errors" gate for specs that intentionally provoke one.
   * Use with `test.use({ allowPageErrors: true })` — and say why in a comment when you do.
   */
  allowPageErrors: boolean
  /** Live buffer of console.error text and uncaught page errors, in arrival order. */
  pageErrors: string[]
  /** A page at /index.html with boot() proven complete. */
  studio: Page
}

export const test = base.extend<StudioFixtures>({
  allowPageErrors: [false, { option: true }],

  pageErrors: async ({ page }, use) => {
    const errors: string[] = []
    page.on('console', (m) => {
      if (m.type() === 'error') errors.push(m.text())
    })
    page.on('pageerror', (e) => errors.push(e.message))
    await use(errors)
  },

  studio: async ({ page, pageErrors, allowPageErrors }, use) => {
    // `pageErrors` is a declared dependency, so its listeners are attached before this navigates —
    // errors thrown during boot are caught, exactly as in the legacy scripts.
    await page.goto('/index.html', { waitUntil: 'load' })
    await waitForStudioBoot(page)

    await use(page)

    // Every legacy script ends its `ok` expression with `&& !errors.length`. Hoisting that here
    // means a spec cannot forget it.
    if (!allowPageErrors) {
      expect(pageErrors, 'console errors / uncaught page errors during the test').toEqual([])
    }
  },
})

export { expect }
