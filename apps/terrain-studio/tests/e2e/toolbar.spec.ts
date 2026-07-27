/**
 * Scalable toolbar regression: profile popover, queued high-res target, command search,
 * graph locator, keyboard access, and compact-width overflow.
 *
 * Converted from terrain-architect/studio/_verify_toolbar.js — one expect() per conjunct of that
 * script's `ok` expression, same order, same literal values.
 */
import { test, expect, attachShot } from './fixtures'

test.describe('@correctness toolbar', () => {
  test('build profile, command palette, locator, and compact overflow', async ({ studio: page }, testInfo) => {
    /* --- initial build profile ---------------------------------------------- */
    const initial = await page.evaluate(() => ({
      res: RES,
      target: TARGET_RES,
      profile: profileRes.textContent,
      overflow: topbar.scrollWidth - topbar.clientWidth,
      resolutions: [...resSel.options].map((o) => +o.value),
    }))
    expect(initial.res).toBe(512)
    expect(initial.target).toBe(512)
    expect(initial.profile).toBe('512²')
    expect(initial.overflow).toBeLessThanOrEqual(1)
    expect(initial.resolutions).toEqual(expect.arrayContaining([512, 1024, 2048, 4096]))

    /* --- profile popover exposes the four build controls --------------------- */
    await page.locator('#buildProfileBtn').click()
    const profileOpen = await page.evaluate(() => ({
      open: !buildSettings.hidden,
      controls: ['resSel', 'qualitySel', 'gpuBtn', 'scaleBtn'].every((id) => !!document.getElementById(id)),
    }))
    expect(profileOpen.open).toBe(true)
    expect(profileOpen.controls).toBe(true)

    /* --- selecting 2048 QUEUES the target, it does not switch the active res -- */
    await page.locator('#resSel').selectOption('2048')
    const queued = await page.evaluate(() => ({
      active: RES,
      target: TARGET_RES,
      auto: AUTO,
      detail: profileDetail.textContent,
    }))
    expect(queued.active).toBe(512)
    expect(queued.target).toBe(2048)
    expect(queued.auto).toBeFalsy()
    expect(queued.detail).toContain('Queued')
    await attachShot(page, testInfo, 'toolbar-profile.png')

    /* --- command palette filters to exactly one hit for "water" -------------- */
    await page.locator('#commandBtn').click()
    await page.locator('#commandSearch').fill('water')
    const filtered = await page.evaluate(() => ({
      profileClosed: buildSettings.hidden,
      menu: !commandMenu.hidden,
      visible: [...document.querySelectorAll<HTMLElement>('.command-item:not(.hidden)')].map(
        (x) => x.dataset.action || x.id,
      ),
    }))
    expect(filtered.profileClosed).toBe(true)
    expect(filtered.menu).toBe(true)
    expect(filtered.visible).toHaveLength(1)
    expect(filtered.visible[0]).toBe('find-water')

    /* --- the locator selects the water node and closes the palette ----------- */
    await page.locator('.command-item[data-action="find-water"]').click()
    await page.waitForFunction(() => commandMenu.hidden)
    const located = await page.evaluate(() => ({
      selected: selected && selected.type,
      menuClosed: commandMenu.hidden,
    }))
    expect(located.selected).toBe('water')
    expect(located.menuClosed).toBe(true)

    /* --- Ctrl+K reopens it -------------------------------------------------- */
    await page.keyboard.press('Control+K')
    await page.waitForFunction(() => !commandMenu.hidden)
    expect(await page.evaluate(() => !commandMenu.hidden)).toBe(true)
    await page.keyboard.press('Escape')

    /* --- compact width: the toolbar scales instead of overflowing ------------ */
    await page.setViewportSize({ width: 760, height: 720 })
    await expect
      .poll(() => page.evaluate(() => getComputedStyle(document.querySelector('.top-io')!).display))
      .toBe('none')
    const compact = await page.evaluate(() => {
      const r = topbar.getBoundingClientRect()
      return {
        overflow: topbar.scrollWidth - topbar.clientWidth,
        commandRight: commandBtn.getBoundingClientRect().right <= r.right + 1,
        ioDisplay: getComputedStyle(document.querySelector('.top-io')!).display,
      }
    })
    expect(compact.overflow).toBeLessThanOrEqual(1)
    expect(compact.commandRight).toBe(true)
    expect(compact.ioDisplay).toBe('none')
    await attachShot(page, testInfo, 'toolbar-compact.png')

    // `&& !errors.length` from the legacy script is enforced by the `studio` fixture teardown.
  })
})
