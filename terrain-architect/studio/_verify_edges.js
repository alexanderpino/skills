// Edge UX + semantics regression: generous curve hit target, selection details,
// mute, context actions, keyboard/handle deletion, undo, and Color Erosion masks.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1400);

  const mask = await page.evaluate(() => {
    const ce = nodes.find(n => n.type === 'colorerosion');
    const satEdge = inputEdge(ce.id, 0), sat = nodeById(satEdge.from);
    const base = resolveColor(sat.id, RES), N = RES * RES;
    const old = { ...ce.params }, oldMask = ce._mask;
    ce.params.density = 1; ce.params.blend = 1; ce.params.transport = 2.2;
    const zero = new Float32Array(N), one = new Float32Array(N); one.fill(1);
    const half = new Float32Array(N);
    for (let y = 0; y < RES; y++) for (let x = RES >> 1; x < RES; x++) half[y * RES + x] = 1;
    const resolve = m => { ce._mask = m; return resolveColor(ce.id, RES); };
    const c0 = resolve(zero), c1 = resolve(one), ch = resolve(half);
    const maskNode = makeNode('constant', 720, 700);maskNode.params.value = 0;
    edges.push({ from: maskNode.id, to: ce.id, slot: 2 });
    nodes.forEach(n => n._dirty = true);evalGraph();
    const graph0 = resolveColor(ce.id, RES);
    maskNode.params.value = 1;markDirtyFrom(maskNode.id);evalGraph();
    const graph1 = resolveColor(ce.id, RES);
    let z = 0, full = 0, left = 0, right = 0, graphZero = 0, graphFull = 0, ln = 0, rn = 0;
    for (let i = 0; i < N; i++) {
      let d0 = 0, d1 = 0, dh = 0, dg0 = 0, dg1 = 0;
      for (let c = 0; c < 3; c++) {
        const j = i * 3 + c; d0 += Math.abs(c0[j] - base[j]); d1 += Math.abs(c1[j] - base[j]); dh += Math.abs(ch[j] - base[j]);
        dg0 += Math.abs(graph0[j] - base[j]);dg1 += Math.abs(graph1[j] - base[j]);
      }
      z += d0 / 3; full += d1 / 3;graphZero += dg0 / 3;graphFull += dg1 / 3;
      if ((i % RES) < (RES >> 1)) { left += dh / 3; ln++; } else { right += dh / 3; rn++; }
    }
    edges = edges.filter(e => e.from !== maskNode.id && e.to !== maskNode.id);nodes = nodes.filter(n => n.id !== maskNode.id);
    ce.params = old;ce._mask = oldMask;nodes.forEach(n => n._dirty = true);evalGraph();
    return { zero: z / N, full: full / N, left: left / ln, right: right / rn,
      graphZero: graphZero / N, graphFull: graphFull / N };
  });

  const target = await page.evaluate(() => {
    const e = edges.find(x => nodeById(x.from)?.type === 'd_deposits' && nodeById(x.to)?.type === 'colorerosion');
    const a = nodeById(e.from), b = nodeById(e.to);
    const p = wirePoint(portPos(a, 'out'), portPos(b, 'in', e.slot), .5);
    return { key: edgeKey(e), x: p.x * view.z + view.x, y: p.y * view.z + view.y };
  });
  const graph = await page.locator('#graph').boundingBox();
  await page.mouse.click(graph.x + target.x, graph.y + target.y);
  const selected = await page.evaluate(() => ({
    key: selectedEdge,
    title: document.querySelector('#pTitle').firstChild.textContent,
    sub: document.querySelector('#pSub').textContent,
    stats: document.querySelectorAll('.edge-stat').length,
    hasDisconnect: [...document.querySelectorAll('#pBody button')].some(b => b.textContent === 'Disconnect')
  }));
  await page.getByRole('button', { name: 'Muted', exact: true }).click();
  const muted = await page.evaluate(() => {
    const e = edgeByKey(selectedEdge);
    return { disabled: e.disabled, activeInput: !!inputEdge(e.to, e.slot), label: document.querySelector('#pSwatch').style.background };
  });
  await page.getByRole('button', { name: 'Enabled', exact: true }).click();

  await page.mouse.click(graph.x + target.x, graph.y + target.y, { button: 'right' });
  const context = await page.evaluate(() => ({
    open: graphMenu.classList.contains('open'),
    labels: [...graphMenu.querySelectorAll('.graph-menu-item')].map(x => x.textContent.trim())
  }));
  await page.keyboard.press('Escape');

  const beforeDelete = await page.evaluate(() => edges.length);
  await page.keyboard.press('Delete');
  const keyboardDelete = await page.evaluate(() => ({ count: edges.length, selectedEdge }));
  await page.keyboard.press('Control+z');
  const undoKeyboard = await page.evaluate(() => ({ count: edges.length, selectedEdge, restored: !!edgeByKey(selectedEdge) }));
  await page.screenshot({ path: path.resolve(__dirname, '_shot_edge_selected.png') });

  const handle = await page.evaluate(() => {
    const e = edgeByKey(selectedEdge), a = nodeById(e.from), b = nodeById(e.to);
    const p = wirePoint(portPos(a, 'out'), portPos(b, 'in', e.slot), .5);
    return { x: p.x * view.z + view.x, y: p.y * view.z + view.y };
  });
  await page.mouse.click(graph.x + handle.x, graph.y + handle.y);
  const handleDelete = await page.evaluate(() => ({ count: edges.length, selectedEdge }));
  await page.keyboard.press('Control+z');
  const inputPort = await page.evaluate(() => {
    const out = outputNode(), e = inputEdge(out.id, 0), p = portPos(out, 'in', 0);
    return { key: edgeKey(e), x: p.x * view.z + view.x, y: p.y * view.z + view.y };
  });
  await page.mouse.click(graph.x + inputPort.x, graph.y + inputPort.y, { button: 'right' });
  const portContext = await page.evaluate(() => ({
    selectedEdge,
    open: graphMenu.classList.contains('open'),
    title: graphMenu.querySelector('.graph-menu-title')?.textContent
  }));

  const report = { mask, target, selected, muted, context, beforeDelete, keyboardDelete, undoKeyboard,
    handleDelete, inputPort, portContext, errors };
  const ok = mask.zero < 1e-8 && mask.full > 1e-4 && mask.left < 1e-8 && mask.right > 1e-4
    && mask.graphZero < 1e-8 && mask.graphFull > 1e-4
    && selected.key === target.key && selected.title === 'Connection'
    && selected.sub.includes('Deposits') && selected.sub.includes('Color Erosion')
    && selected.stats === 3 && selected.hasDisconnect
    && muted.disabled && !muted.activeInput
    && context.open
    && context.labels.some(x => x.includes('Connection properties'))
    && context.labels.some(x => x.includes('Mute connection'))
    && context.labels.some(x => x.includes('Disconnect'))
    && keyboardDelete.count === beforeDelete - 1 && keyboardDelete.selectedEdge === null
    && undoKeyboard.count === beforeDelete && undoKeyboard.restored
    && handleDelete.count === beforeDelete - 1 && handleDelete.selectedEdge === null
    && portContext.open && portContext.title === 'Connection' && portContext.selectedEdge === inputPort.key
    && !errors.length;
  console.log(JSON.stringify({ ...report, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
