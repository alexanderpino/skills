// Drag-out quick create: releasing a connection on empty graph space opens a searchable,
// connectable-only node picker; choosing a node creates + links it as one undoable edit.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1400);

  const graph = await page.locator('#graph').boundingBox();
  if (!graph) throw new Error('SETUP FAILURE: graph canvas has no bounding box');
  const setup = await page.evaluate(() => {
    const source = nodes.find(n => n.type === 'perlin');
    if (!source) throw new Error('SETUP FAILURE: default graph has no Perlin source');
    const sourcePort = portPos(source, 'out');
    const canvas = document.querySelector('#graph');
    let drop = null;
    for (let y = canvas.clientHeight - 55; y > 70 && !drop; y -= 40) {
      for (let x = canvas.clientWidth - 90; x > 280; x -= 50) {
        const w = { x: (x - view.x) / view.z, y: (y - view.y) / view.z };
        const occupied = nodes.some(n => w.x >= n.x - 18 && w.x <= n.x + n.w + 18
          && w.y >= n.y - 18 && w.y <= n.y + 150);
        if (!occupied) {
          drop = { x, y, worldX: w.x, worldY: w.y }; break;
        }
      }
    }
    if (!drop) throw new Error('SETUP FAILURE: no empty quick-create drop point');
    return {
      sourceId: source.id,
      source: { x: sourcePort.x * view.z + view.x, y: sourcePort.y * view.z + view.y },
      drop, nodes: nodes.length, edges: edges.length, undo: undoStack.length
    };
  });

  await page.mouse.move(graph.x + setup.source.x, graph.y + setup.source.y);
  await page.mouse.down();
  await page.mouse.move(graph.x + setup.drop.x, graph.y + setup.drop.y, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(100);

  const picker = await page.evaluate(() => {
    const items = [...document.querySelectorAll('#menu .menu-item')];
    return {
      open: document.querySelector('#menu').classList.contains('open'),
      context: document.querySelector('#menu .menu-context')?.textContent || '',
      search: !!document.querySelector('#menu .menu-search'),
      focused: document.activeElement?.classList.contains('menu-search'),
      itemCount: items.length,
      incompatible: items.filter(el => !(TYPES[el.dataset.type]?.ins?.length)).map(el => el.dataset.type)
    };
  });
  await page.screenshot({ path: path.resolve(__dirname, '_shot_quick_create.png') });

  await page.locator('#menu .menu-search').fill('Thermal');
  const filtered = await page.evaluate(() => [...document.querySelectorAll('#menu .menu-item')]
    .map(el => el.dataset.type));
  await page.locator('#menu .menu-search').press('Enter');
  await page.waitForTimeout(180);

  const created = await page.evaluate(({ sourceId, drop }) => {
    const node = selected;
    const edge = node && edges.find(e => e.from === sourceId && e.to === node.id);
    return {
      type: node?.type, nodeCount: nodes.length, edgeCount: edges.length,
      edge: edge && { from: edge.from, to: edge.to, slot: edge.slot },
      center: node && { x: node.x + node.w / 2, y: node.y + 30 },
      dropWorld: { x: drop.worldX, y: drop.worldY },
      menuOpen: document.querySelector('#menu').classList.contains('open'),
      undo: undoStack.length
    };
  }, { sourceId: setup.sourceId, drop: setup.drop });

  await page.keyboard.press('Control+z');
  const undone = await page.evaluate(() => ({
    nodes: nodes.length, edges: edges.length,
    hasThermal: nodes.some(n => n.type === 'thermal')
  }));
  await page.keyboard.press('Control+y');
  const redone = await page.evaluate(({ sourceId }) => {
    const node = nodes.find(n => n.type === 'thermal');
    return {
      nodes: nodes.length, edges: edges.length, thermalId: node?.id,
      connected: !!node && edges.some(e => e.from === sourceId && e.to === node.id && e.slot === 0)
    };
  }, { sourceId: setup.sourceId });

  // Canceling a second drag-out must leave both graph topology and history untouched.
  const cancelBefore = await page.evaluate(() => ({ nodes: nodes.length, edges: edges.length, undo: undoStack.length }));
  await page.mouse.move(graph.x + setup.source.x, graph.y + setup.source.y);
  await page.mouse.down();
  await page.mouse.move(graph.x + setup.drop.x, graph.y + setup.drop.y, { steps: 5 });
  await page.mouse.up();
  await page.locator('#menu .menu-search').press('Escape');
  const canceled = await page.evaluate(() => ({
    nodes: nodes.length, edges: edges.length, undo: undoStack.length,
    menuOpen: document.querySelector('#menu').classList.contains('open')
  }));

  const report = { setup, picker, filtered, created, undone, redone, cancelBefore, canceled, errors };
  const ok = picker.open && picker.search && picker.focused
    && picker.context.includes('Perlin') && picker.itemCount > 0 && picker.incompatible.length === 0
    && filtered.includes('thermal') && filtered[0] === 'thermal'
    && created.type === 'thermal'
    && created.nodeCount === setup.nodes + 1 && created.edgeCount === setup.edges + 1
    && created.edge?.from === setup.sourceId && created.edge?.slot === 0
    && Math.abs(created.center.x - created.dropWorld.x) < .01
    && Math.abs(created.center.y - created.dropWorld.y) < .01
    && !created.menuOpen && created.undo === setup.undo + 1
    && undone.nodes === setup.nodes && undone.edges === setup.edges && !undone.hasThermal
    && redone.nodes === setup.nodes + 1 && redone.edges === setup.edges + 1 && redone.connected
    && canceled.nodes === cancelBefore.nodes && canceled.edges === cancelBefore.edges
    && canceled.undo === cancelBefore.undo && !canceled.menuOpen
    && !errors.length;
  console.log(JSON.stringify({ ...report, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
