// Graph organization regression: deterministic layered layout, branch scopes,
// undo, context-menu actions, and the editor-only/no-terrain-rebuild contract.
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

  // BUILD THE DOCUMENT THIS FILE MEASURES. D7 (31f5688) demoted the 18-node showcase to the
  // page-global showcaseGraph() and made the opening document L0 - 7 nodes, one branch point.
  // Measured before this block: FATAL "Cannot read properties of undefined (reading 'id')" at
  // anchor.id, because the branch-scope probe anchors on 'weathering', which L0 does not have.
  // L0 is also too thin to be a layout regression surface at all: the whole point of the branch
  // scope check is branch.scope < branch.all, i.e. a graph with a genuine off-branch remainder.
  //
  // evalGraph() is enough here; a full #buildBtn rebuild is NOT needed - and evalGraph() is
  // REQUIRED, not optional. organizeGraph is an editor-only operation and the central contract
  // is that it does not touch terrain: fieldStable/undoFieldStable/redoFieldStable compare
  // outputNode()._field by IDENTITY. Without an evaluation those are undefined === undefined -
  // three assertions that pass on any behaviour whatsoever. evalGraph() makes _field a real
  // Float32Array so the identity comparison has something to be wrong about. Nothing here reads
  // curHgt/curFilled/curAccum or renders, so the renderer caches are outside the measurement.
  await page.evaluate(() => {
    nodes.length = 0; edges.length = 0; uid = 1; selected = null; selectedEdge = null;
    showcaseGraph(); evalGraph();
  });
  await page.waitForTimeout(200);

  const layout = await page.evaluate(() => {
    const out0 = outputNode();
    if (!out0) throw new Error('SETUP FAILURE: no output node after showcaseGraph()');
    if (!out0._field) throw new Error('SETUP FAILURE: output node has no _field - evalGraph() did not run, the *FieldStable checks would be vacuous');
    const field = outputNode()._field;
    const dirty = nodes.map(n => [n.id, !!n._dirty]);
    const undoBefore = undoStack.length;
    nodes.forEach((n, i) => {
      n.x = ((i * 83) % 410) - 190;
      n.y = ((i * 137) % 330) - 145;
    });
    const first = organizeGraph();
    const positions = nodes.map(n => [n.id, n.x, n.y]);
    const organizedField = outputNode()._field;
    const rectangles = nodes.map(n => ({
      id: n.id, x0: n.x, y0: n.y, x1: n.x + n.w, y1: n.y + nodeH(n)
    }));
    const overlaps = [];
    for (let i = 0; i < rectangles.length; i++) for (let j = i + 1; j < rectangles.length; j++) {
      const a = rectangles[i], b = rectangles[j];
      if (a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0) overlaps.push([a.id, b.id]);
    }
    const backwards = edges.filter(e => {
      const a = nodeById(e.from), b = nodeById(e.to);
      return a.x + a.w >= b.x;
    }).map(e => [e.from, e.to]);
    const editorOnlySnapshot = snapshotIsEditorOnly(undoStack[undoStack.length - 1]);
    undoGraph();
    const undoRestored = nodes.every((n, i) =>
      n.x === (((i * 83) % 410) - 190) && n.y === (((i * 137) % 330) - 145));
    const undoFieldStable = outputNode()._field === organizedField;
    redoGraph();
    const redoRestored = JSON.stringify(nodes.map(n => [n.id, n.x, n.y])) === JSON.stringify(positions);
    const redoFieldStable = outputNode()._field === organizedField;
    const second = organizeGraph();
    const positions2 = nodes.map(n => [n.id, n.x, n.y]);
    return {
      first, second, overlaps, backwards, editorOnlySnapshot,
      repeatStable: JSON.stringify(positions) === JSON.stringify(positions2),
      undoRestored, redoRestored, undoFieldStable, redoFieldStable,
      fieldStable: outputNode()._field === field,
      dirtyStable: JSON.stringify(nodes.map(n => [n.id, !!n._dirty])) === JSON.stringify(dirty),
      undoAdded: undoStack.length - undoBefore
    };
  });

  const branch = await page.evaluate(() => {
    const anchor = nodes.find(n => n.type === 'weathering');
    if (!anchor) throw new Error('SETUP FAILURE: no weathering node after showcaseGraph()');
    const ids = graphIdsFrom(anchor.id, 'up');
    if (!ids || !ids.size) throw new Error('SETUP FAILURE: empty upstream scope for weathering');
    const outside = nodes.filter(n => !ids.has(n.id));
    const outsideBefore = outside.map(n => [n.id, n.x, n.y]);
    nodes.filter(n => ids.has(n.id)).forEach((n, i) => { n.x += (i % 2 ? 91 : -74); n.y += i * 17; });
    const anchorBefore = [anchor.x, anchor.y];
    const result = organizeGraph(ids, anchor.id, 'Organized upstream');
    return {
      result,
      anchorStable: anchor.x === anchorBefore[0] && anchor.y === anchorBefore[1],
      outsideStable: JSON.stringify(outside.map(n => [n.id, n.x, n.y])) === JSON.stringify(outsideBefore),
      scope: ids.size,
      all: nodes.length
    };
  });

  const graphBox = await page.locator('#graph').boundingBox();
  await page.mouse.click(graphBox.x + graphBox.width - 24, graphBox.y + graphBox.height - 24, { button: 'right' });
  const blankMenu = await page.evaluate(() => ({
    open: graphMenu.classList.contains('open'),
    labels: [...graphMenu.querySelectorAll('.graph-menu-item')].map(x => x.textContent.trim())
  }));
  await page.keyboard.press('Escape');

  const nodePoint = await page.evaluate(() => {
    const n = nodes.find(x => x.type === 'weathering');
    if (!n) throw new Error('SETUP FAILURE: no weathering node to right-click');
    return { x: n.x * view.z + view.x + 30, y: n.y * view.z + view.y + 24 };
  });
  await page.mouse.click(graphBox.x + nodePoint.x, graphBox.y + nodePoint.y, { button: 'right' });
  const nodeMenu = await page.evaluate(() => ({
    open: graphMenu.classList.contains('open'),
    labels: [...graphMenu.querySelectorAll('.graph-menu-item')].map(x => x.textContent.trim())
  }));
  await page.screenshot({ path: path.resolve(__dirname, '_shot_organize.png') });

  const context = {
    blank: blankMenu.open
      && blankMenu.labels.some(x => x.includes('Add node here'))
      && blankMenu.labels.some(x => x.includes('Organize all nodes'))
      && blankMenu.labels.some(x => x.includes('Frame all nodes')),
    node: nodeMenu.open
      && nodeMenu.labels.some(x => x.includes('Organize connected branch'))
      && nodeMenu.labels.some(x => x.includes('Organize upstream'))
      && nodeMenu.labels.some(x => x.includes('Organize downstream'))
      && nodeMenu.labels.some(x => x.includes('Frame connected branch'))
      && nodeMenu.labels.some(x => x.includes('Duplicate'))
      && nodeMenu.labels.some(x => x.includes('Delete'))
  };
  const report = { layout, branch, blankMenu, nodeMenu, context, errors };
  const ok = layout.first.changed && layout.first.count > 1
    && !layout.overlaps.length && !layout.backwards.length
    && layout.editorOnlySnapshot && !layout.second.changed && layout.repeatStable
    && layout.undoRestored && layout.redoRestored
    && layout.undoFieldStable && layout.redoFieldStable
    && layout.fieldStable && layout.dirtyStable && layout.undoAdded === 1
    && branch.result.changed && branch.anchorStable && branch.outsideStable
    && branch.scope < branch.all
    && context.blank && context.node
    && !errors.length;
  console.log(JSON.stringify({ ...report, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
