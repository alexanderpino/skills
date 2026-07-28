/**
 * Application-menu regression: responsive desktop/hamburger states, shared commands,
 * safe new-document reset, default starter restoration, and topbar overflow.
 *
 * Converted from terrain-architect/studio/_verify_menubar.js. Every conjunct of that script's
 * single `ok` expression appears below as its own expect(), in the same order, with the same
 * literal values — a failure now names the clause instead of printing `ok: false`.
 */
import { test, expect, attachShot } from './fixtures'

test.describe('@correctness application menu', () => {
  test('desktop menubar, document reset, and compact hamburger', async ({ studio: page }, testInfo) => {
    /* --- desktop state at 1440x900 ------------------------------------------ */
    const desktop = await page.evaluate(() => ({
      desktopDisplay: getComputedStyle(document.querySelector('.desktop-menu')!).display,
      compactDisplay: getComputedStyle(document.querySelector('.compact-menu-wrap')!).display,
      topbarOverflow: topbar.scrollWidth - topbar.clientWidth,
      headings: [...document.querySelectorAll('.editor-menu-trigger')].map((b) => b.textContent!.trim()),
    }))
    expect(desktop.desktopDisplay).toBe('flex')
    expect(desktop.compactDisplay).toBe('none')
    expect(desktop.topbarOverflow).toBeLessThanOrEqual(1)
    expect(desktop.headings).toEqual(['File', 'Edit', 'View', 'Help'])

    /* --- File menu opens and carries the shared command set ------------------ */
    await page.locator('#fileMenuBtn').click()
    const fileOpen = await page.evaluate(() => ({
      open: !fileMenu.hidden,
      commands: [...fileMenu.querySelectorAll<HTMLElement>('[data-editor-command]')].map(
        (b) => b.dataset.editorCommand,
      ),
    }))
    expect(fileOpen.open).toBe(true)
    expect(fileOpen.commands).toEqual(expect.arrayContaining(['new', 'new-default', 'import', 'export']))
    await attachShot(page, testInfo, 'menubar-desktop.png')

    /* --- File > New: confirm dialog, then a clean single-output document ----- */
    page.once('dialog', (d) => d.accept())
    await page.locator('#fileMenu [data-editor-command="new"]').click()
    // newTerrainDocument() is synchronous through evalGraph(), so the graph is already rebuilt by
    // the time the click settles; wait on the shape rather than on the legacy 120 ms sleep.
    await page.waitForFunction(() => nodes.length === 1)
    const blank = await page.evaluate(() => ({
      types: nodes.map((n) => n.type),
      edges: edges.length,
      undo: undoStack.length,
      redo: redoStack.length,
      selected: selected && selected.type,
      outputReady: !!(outputNode() && outputNode()!._field),
      organization: (() => {
        const n = nodes[0]
        return {
          zoom: view.z,
          centerErrorX: Math.abs(view.x + (n.x + n.w / 2) * view.z - gc.clientWidth / 2),
          centerErrorY: Math.abs(view.y + (n.y + nodeH(n) / 2) * view.z - gc.clientHeight / 2),
        }
      })(),
    }))
    expect(blank.types).toEqual(['output'])
    expect(blank.edges).toBe(0)
    expect(blank.undo).toBeFalsy()
    expect(blank.redo).toBeFalsy()
    expect(blank.selected).toBe('output')
    expect(blank.outputReady).toBe(true)
    expect(blank.organization.zoom).toBe(1.35)
    expect(blank.organization.centerErrorX).toBeLessThanOrEqual(0.5)
    expect(blank.organization.centerErrorY).toBeLessThanOrEqual(0.5)

    /* --- File > New from default setup: the production starter graph is back -- */
    await page.locator('#fileMenuBtn').click()
    page.once('dialog', (d) => d.accept())
    await page.locator('#fileMenu [data-editor-command="new-default"]').click()
    await page.waitForFunction(() => nodes.length >= 16)
    const starter = await page.evaluate(() => ({
      count: nodes.length,
      types: nodes.map((n) => n.type),
      edges: edges.length,
      selected: selected && selected.type,
      undo: undoStack.length,
    }))
    expect(starter.count).toBeGreaterThanOrEqual(16)
    expect(starter.edges).toBeGreaterThanOrEqual(18)
    expect(starter.types).toContain('water')
    expect(starter.types).toContain('snow')
    expect(starter.types).toContain('d_temperature')
    expect(starter.selected).toBe('satmap')
    expect(starter.undo).toBeFalsy()

    /* --- compact breakpoint: hamburger replaces the menubar, still no overflow */
    await page.setViewportSize({ width: 760, height: 720 })
    await expect
      .poll(() => page.evaluate(() => getComputedStyle(document.querySelector('.desktop-menu')!).display))
      .toBe('none')
    const compact = await page.evaluate(() => ({
      desktopDisplay: getComputedStyle(document.querySelector('.desktop-menu')!).display,
      compactDisplay: getComputedStyle(document.querySelector('.compact-menu-wrap')!).display,
      overflow: topbar.scrollWidth - topbar.clientWidth,
    }))
    expect(compact.desktopDisplay).toBe('none')
    expect(compact.compactDisplay).toBe('block')
    expect(compact.overflow).toBeLessThanOrEqual(1)

    await page.locator('#mainMenuBtn').click()
    const compactOpen = await page.evaluate(() => ({
      open: !mainMenu.hidden,
      sections: [...document.querySelectorAll('.compact-menu-section')].map((b) =>
        b.textContent!.trim().replace('›', '').trim(),
      ),
    }))
    expect(compactOpen.open).toBe(true)
    expect(compactOpen.sections).toEqual(['▱File', '✎Edit', '▣View', '?Help'])

    /* --- the compact File section exposes the same commands as the desktop one */
    await page.locator('[data-compact-section="compactFile"]').click()
    const compactFileState = await page.evaluate(() => ({
      open: !compactFile.hidden,
      commands: [...compactFile.querySelectorAll<HTMLElement>('[data-editor-command]')].map(
        (b) => b.dataset.editorCommand,
      ),
    }))
    expect(compactFileState.open).toBe(true)
    expect(compactFileState.commands).toEqual(
      expect.arrayContaining(['new', 'new-default', 'import', 'export']),
    )
    await attachShot(page, testInfo, 'menubar-compact.png')

    /* --- Escape closes the whole shell -------------------------------------- */
    await page.keyboard.press('Escape')
    expect(await page.evaluate(() => mainMenu.hidden)).toBe(true)

    // `&& !errors.length` from the legacy script is enforced by the `studio` fixture teardown.
  })
})
