/**
 * Deep viewport navigation: cursor-focused dolly, movable pivot, surface lock, adaptive near plane,
 * right-drag pan, and deterministic frame reset.
 *
 * Converted from terrain-architect/studio/_verify_zoom.js — one expect() per conjunct of that
 * script's `ok` expression, same order, same literal tolerances (.01201, 3e-4, 1e-6, 1e-5, 1e-9, 2.6).
 *
 * Tagged @timing, not @correctness. The assertions are geometric, but reaching them requires the
 * live SwiftShader render loop to deliver all 24 discrete wheel events to a rAF-driven camera; under
 * CPU contention wheel deltas coalesce and `cam.dist` never reaches its clamp. This is the spec that
 * pays for `workers: 1`.
 *
 * NOTE — the legacy script launches with a FIFTH flag, `--ignore-gpu-blocklist`, that the other 49
 * scripts do not use. It is inert here: `--use-gl=angle --use-angle=swiftshader` selects the
 * software rasteriser explicitly, so there is no hardware driver left for a blocklist to veto. The
 * shared project keeps the canonical four flags rather than special-casing one spec.
 */
import { test, expect, attachShot, settle } from './fixtures'

const HERO_TARGET = [0, 0.05, 0] as const

test.describe('@timing viewport navigation', () => {
  test('right-drag pan, cursor-focused deep dolly, and frame reset', async ({ studio: page }, testInfo) => {
    /* --- side-by-side layout, then a clean 512² rebuild ---------------------- */
    await page.locator('#layoutBtn').click()
    // setLayout() defers resizeGraph()/resizeGL() to the next frame, so the viewport box is only
    // trustworthy after a frame has actually run.
    await settle(page)

    await page.evaluate(() => {
      RES = 512
      buildIndex()
      nodes.forEach((n) => {
        n._dirty = true
        n._thumb = null
      })
      evalGraph()
    })
    await settle(page)

    const r = (await page.locator('#viewport').boundingBox())!
    expect(r).not.toBeNull()

    /* --- right-drag pans the inspection pivot before zooming ----------------- */
    await page.mouse.move(r.x + r.width * 0.5, r.y + r.height * 0.5)
    await page.mouse.down({ button: 'right' })
    await page.mouse.move(r.x + r.width * 0.58, r.y + r.height * 0.46, { steps: 5 })
    await page.mouse.up({ button: 'right' })
    const afterPan = await page.evaluate(() => ({ dist: cam.dist, target: [...cam.target] }))

    const panMoved = Math.hypot(
      afterPan.target[0],
      afterPan.target[1] - HERO_TARGET[1],
      afterPan.target[2],
    )
    expect(panMoved, 'pivot moved off the hero target').toBeGreaterThan(0.01)

    /* --- dolly repeatedly toward an off-centre cursor ------------------------
     * The target should travel under that cursor and settle onto the sampled terrain surface
     * while distance reaches the deep-inspection clamp. */
    await page.mouse.move(r.x + r.width * 0.72, r.y + r.height * 0.43)
    for (let i = 0; i < 24; i++) await page.mouse.wheel(0, -240)
    await expect.poll(() => page.evaluate(() => cam.dist)).toBeLessThanOrEqual(0.01201)

    const deep = await page.evaluate(() => {
      const eye = cameraEye()
      const d = Math.hypot(eye[0] - cam.target[0], eye[1] - cam.target[1], eye[2] - cam.target[2])
      return {
        dist: cam.dist,
        near: cameraNear(),
        target: [...cam.target],
        eyeDistance: d,
        surface: surfaceHeight(cam.target[0], cam.target[2]),
        glError: gl.getError(),
      }
    })

    const focusMoved = Math.hypot(deep.target[0] - afterPan.target[0], deep.target[2] - afterPan.target[2])
    expect(focusMoved, 'dolly dragged the pivot toward the cursor').toBeGreaterThan(0.01)
    expect(deep.dist, 'deep-inspection distance clamp').toBeLessThanOrEqual(0.01201)
    expect(deep.near, 'near plane adapts to the clamped distance').toBeLessThan(0.0003)
    expect(Math.abs(deep.eyeDistance - deep.dist), 'eye sits exactly cam.dist from the pivot').toBeLessThan(1e-6)
    expect(Math.abs(deep.target[1] - deep.surface), 'pivot locked to the sampled surface').toBeLessThan(1e-5)
    expect(deep.glError, 'no WebGL error after the dolly').toBe(0)
    await attachShot(page, testInfo, 'zoom-deep.png')

    /* --- 'f' restores the deterministic hero frame --------------------------- */
    await page.keyboard.press('f')
    await page.waitForFunction(() => cam.dist === 2.6)
    const framed = await page.evaluate(() => ({
      dist: cam.dist,
      target: [...cam.target],
      az: cam.az,
      el: cam.el,
      planView,
    }))
    expect(framed.dist).toBe(2.6)
    framed.target.forEach((v, i) => {
      expect(Math.abs(v - HERO_TARGET[i]), `hero target component ${i}`).toBeLessThan(1e-9)
    })
    expect(framed.planView).toBeFalsy()

    // `&& !errors.length` from the legacy script is enforced by the `studio` fixture teardown.
  })
})
