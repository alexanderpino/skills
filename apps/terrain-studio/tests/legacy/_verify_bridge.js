// Phase 0 of the ES-module refactor: freeze the exact global surface that the
// verification suite reaches into, so "will the test bridge cover everything?"
// becomes a mechanical diff against bridge-surface.json instead of a gamble.
//
// index.html is a single-file app with ONE inline classic <script>, so every
// top-level let/const/function in it is a real global. The _verify_*.js
// Playwright scripts reach those globals from inside page.evaluate(...) bodies.
// Bundling to ES modules will scope every one of them; a test bridge must
// re-expose them on window. This script derives that list.
//
// Method: real AST parsing (acorn) + a scope walker. Every page-side callback
// (evaluate / evaluateHandle / waitForFunction / $eval / $$eval / evaluateAll /
// addInitScript) is parsed, its own bindings resolved, and the identifiers that
// resolve to nothing inside the callback are page globals by definition.
//
// This script needs no browser -- it is a static analysis, not a Playwright run.
//
//   npm i acorn --no-save
//   node _verify_bridge.js            re-freeze bridge-surface.json from the tree
//   node _verify_bridge.js --check    GATE: exit 1 if the live surface has drifted
//
// --check is the whole point: after the ESM split, run it and "did the bridge
// cover everything?" is answered by a diff instead of by discovering a missing
// global halfway through the suite.
//
// Deterministic: no timestamps, stable sort — reruns produce a byte-identical
// bridge-surface.json unless the real surface changed.
'use strict';

const fs = require('fs');
const path = require('path');

let acorn = null;
try { acorn = require('acorn'); } catch (_) { /* handled below */ }
if (!acorn) {
  console.error([
    'FATAL: acorn is not installed.',
    '',
    'This script deliberately refuses to fall back to regex scanning: a regex',
    'cannot tell a page global from a callback local, an object-literal key, or',
    'a non-computed member name, and the whole value of bridge-surface.json is',
    'that it is complete and has no false entries.',
    '',
    '  npm i acorn --no-save',
  ].join('\n'));
  process.exit(2);
}

const DIR = __dirname;
const SELF = path.basename(__filename);
// ../../index.html, not ./index.html. This tool was written when it sat beside the app; the suite
// then moved into tests/legacy/ and the path was never updated, so APP pointed at a file that does
// not exist. Combined with acorn being uninstalled (the exit(2) above fires first), the tool has
// been unrunnable — which is exactly why bridge-surface.json is a fossil: its meta still records
// scriptLines "920-7623" and 56 test files against an app that is now 928-8110 with 66 oracles.
// A frozen contract that cannot be regenerated stops being a contract and becomes a rumour.
const APP = process.env.BRIDGE_APP
  ? path.resolve(process.env.BRIDGE_APP)
  : path.resolve(DIR, '../../index.html');
const OUT = path.join(DIR, 'bridge-surface.json');
if (!fs.existsSync(APP)) {
  console.error(`FATAL: app not found at ${APP}\n  set BRIDGE_APP to override.`);
  process.exit(2);
}

// Playwright methods whose function argument is serialized and run in the page.
const PAGE_SIDE = new Set([
  'evaluate', 'evaluateHandle', 'evaluateAll', 'waitForFunction',
  '$eval', '$$eval', 'addInitScript',
]);

// ---------------------------------------------------------------------------
// Deny-list: JS + DOM builtins. Only consulted for identifiers that are NOT
// declared at index.html top level -- a real app global always wins, so an
// app symbol that happens to collide with a builtin name (e.g. GPU) is never
// swallowed by this list.
// ---------------------------------------------------------------------------
const BUILTINS = new Set([
  // --- ECMAScript intrinsics / global functions ---
  'globalThis', 'undefined', 'NaN', 'Infinity', 'eval', 'isFinite', 'isNaN',
  'parseFloat', 'parseInt', 'decodeURI', 'decodeURIComponent', 'encodeURI',
  'encodeURIComponent', 'escape', 'unescape', 'structuredClone', 'queueMicrotask',
  'Object', 'Function', 'Boolean', 'Symbol', 'BigInt', 'Number', 'String',
  'Math', 'Date', 'RegExp', 'JSON', 'Promise', 'Reflect', 'Proxy', 'Intl',
  'Array', 'Int8Array', 'Uint8Array', 'Uint8ClampedArray', 'Int16Array',
  'Uint16Array', 'Int32Array', 'Uint32Array', 'Float16Array', 'Float32Array',
  'Float64Array', 'BigInt64Array', 'BigUint64Array', 'ArrayBuffer',
  'SharedArrayBuffer', 'DataView', 'Atomics',
  'Map', 'Set', 'WeakMap', 'WeakSet', 'WeakRef', 'FinalizationRegistry',
  'Error', 'AggregateError', 'EvalError', 'RangeError', 'ReferenceError',
  'SyntaxError', 'TypeError', 'URIError', 'Iterator', 'AsyncIterator',
  'Generator', 'GeneratorFunction', 'AsyncFunction',
  // --- window / timers / misc browser globals ---
  'window', 'self', 'top', 'parent', 'frames', 'opener', 'closed', 'name',
  'length', 'origin', 'isSecureContext', 'crossOriginIsolated',
  'document', 'console', 'navigator', 'location', 'history', 'screen',
  'localStorage', 'sessionStorage', 'indexedDB', 'caches', 'crypto',
  'performance', 'visualViewport', 'devicePixelRatio', 'customElements',
  'innerWidth', 'innerHeight', 'outerWidth', 'outerHeight', 'scrollX', 'scrollY',
  'pageXOffset', 'pageYOffset', 'screenX', 'screenY',
  'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval',
  'requestAnimationFrame', 'cancelAnimationFrame',
  'requestIdleCallback', 'cancelIdleCallback',
  'getComputedStyle', 'getSelection', 'matchMedia', 'alert', 'confirm', 'prompt',
  'scrollTo', 'scrollBy', 'scroll', 'moveTo', 'moveBy', 'resizeTo', 'resizeBy',
  'open', 'close', 'stop', 'print', 'focus', 'blur', 'postMessage',
  'atob', 'btoa', 'fetch', 'reportError', 'createImageBitmap',
  'addEventListener', 'removeEventListener', 'dispatchEvent',
  // --- constructors / interfaces commonly referenced from page code ---
  'Headers', 'Request', 'Response', 'FormData', 'URL', 'URLSearchParams',
  'Blob', 'File', 'FileReader', 'FileList', 'DataTransfer', 'DataTransferItem',
  'Image', 'Audio', 'Option', 'Worker', 'SharedWorker', 'Worklet',
  'MessageChannel', 'MessagePort', 'BroadcastChannel', 'WebSocket',
  'EventSource', 'XMLHttpRequest', 'AbortController', 'AbortSignal',
  'ReadableStream', 'WritableStream', 'TransformStream',
  'TextEncoder', 'TextDecoder', 'DOMParser', 'XMLSerializer',
  'ResizeObserver', 'IntersectionObserver', 'MutationObserver',
  'PerformanceObserver', 'ReportingObserver',
  'Event', 'CustomEvent', 'EventTarget', 'UIEvent', 'MouseEvent', 'PointerEvent',
  'KeyboardEvent', 'WheelEvent', 'TouchEvent', 'Touch', 'DragEvent',
  'InputEvent', 'FocusEvent', 'ProgressEvent', 'ClipboardEvent',
  'CompositionEvent', 'AnimationEvent', 'TransitionEvent', 'SubmitEvent',
  'MessageEvent', 'ErrorEvent', 'StorageEvent', 'PopStateEvent', 'HashChangeEvent',
  'Node', 'Element', 'Document', 'DocumentFragment', 'ShadowRoot', 'Text',
  'Comment', 'Attr', 'NodeList', 'HTMLCollection', 'NamedNodeMap',
  'NodeFilter', 'NodeIterator', 'TreeWalker', 'Range', 'StaticRange',
  'Selection', 'AbstractRange',
  'DOMRect', 'DOMRectReadOnly', 'DOMPoint', 'DOMPointReadOnly', 'DOMMatrix',
  'DOMMatrixReadOnly', 'DOMQuad', 'DOMException', 'DOMStringMap', 'DOMTokenList',
  'CanvasRenderingContext2D', 'OffscreenCanvas', 'OffscreenCanvasRenderingContext2D',
  'ImageData', 'ImageBitmap', 'Path2D', 'CanvasGradient', 'CanvasPattern',
  'CSS', 'CSSStyleDeclaration', 'CSSStyleSheet', 'StyleSheet', 'StyleSheetList',
  'CSSRule', 'CSSRuleList', 'MediaQueryList', 'MediaQueryListEvent',
  'Storage', 'Notification', 'Navigator', 'Location', 'History', 'Screen',
  'Animation', 'KeyframeEffect', 'IdleDeadline',
  'AudioContext', 'OfflineAudioContext', 'AudioBuffer', 'AudioBufferSourceNode',
  'GainNode', 'AnalyserNode',
  // --- Node-side identifiers that can appear inside a page callback only by
  //     mistake, listed so they surface as builtins rather than app globals ---
  'process', 'Buffer', '__dirname', '__filename',
]);

// Prefix rules for the long tail of DOM/WebGL interfaces. Same precedence
// caveat: an index.html top-level declaration always beats these.
const BUILTIN_PATTERNS = [
  /^WebGL/, /^WebGPU/, /^HTML[A-Za-z]*Element$/, /^SVG[A-Z]/, /^XPath/,
  /^Media[A-Z]/, /^RTC[A-Z]/, /^Speech[A-Z]/, /^IDB[A-Z]/, /^Perf(ormance)?[A-Z]/,
  /^Font[A-Z]/, /^Gamepad/, /^Bluetooth/, /^USB[A-Z]/, /^Payment[A-Z]/,
  /^Credential/, /^Push[A-Z]/, /^Service[A-Z]/, /^Cache[A-Z]?/,
];
const isBuiltin = (n) => BUILTINS.has(n) || BUILTIN_PATTERNS.some((re) => re.test(n));

// ---------------------------------------------------------------------------
// Generic AST traversal helper (no acorn-walk dependency; version-proof).
// ---------------------------------------------------------------------------
function eachChild(node, fn) {
  for (const key of Object.keys(node)) {
    if (key === 'loc' || key === 'range' || key === 'parent') continue;
    const v = node[key];
    if (Array.isArray(v)) {
      for (const c of v) if (c && typeof c.type === 'string') fn(c, key);
    } else if (v && typeof v.type === 'string') {
      fn(v, key);
    }
  }
}

function walkAll(node, fn) {
  fn(node);
  eachChild(node, (c) => walkAll(c, fn));
}

// ---------------------------------------------------------------------------
// Scope model
// ---------------------------------------------------------------------------
const newScope = (parent, kind) => ({ parent, kind, names: new Set() });
function fnScopeOf(s) { while (s && s.kind !== 'function' && s.kind !== 'program') s = s.parent; return s; }
function resolves(scope, name) { for (let s = scope; s; s = s.parent) if (s.names.has(name)) return true; return false; }

function patternNames(node, out) {
  if (!node) return;
  switch (node.type) {
    case 'Identifier': out.push(node.name); break;
    case 'ObjectPattern':
      for (const p of node.properties) {
        if (p.type === 'RestElement') patternNames(p.argument, out);
        else patternNames(p.value, out);
      }
      break;
    case 'ArrayPattern': for (const e of node.elements) patternNames(e, out); break;
    case 'AssignmentPattern': patternNames(node.left, out); break;
    case 'RestElement': patternNames(node.argument, out); break;
    case 'Property': patternNames(node.value, out); break;
    default: break; // MemberExpression targets bind nothing
  }
}

// `var` + FunctionDeclaration hoisting, not crossing function boundaries.
function hoistVars(root, scope) {
  const visit = (n) => {
    if (n.type === 'FunctionDeclaration') { if (n.id) scope.names.add(n.id.name); return; }
    if (n.type === 'FunctionExpression' || n.type === 'ArrowFunctionExpression'
      || n.type === 'ClassDeclaration' || n.type === 'ClassExpression') return;
    if (n.type === 'VariableDeclaration' && n.kind === 'var') {
      const names = [];
      for (const d of n.declarations) patternNames(d.id, names);
      for (const x of names) scope.names.add(x);
    }
    eachChild(n, visit);
  };
  eachChild(root, visit);
}

// let/const/class/function declared directly among these statements.
function hoistLexical(stmts, scope) {
  for (const st of stmts) {
    if (!st) continue;
    if (st.type === 'VariableDeclaration' && st.kind !== 'var') {
      const names = [];
      for (const d of st.declarations) patternNames(d.id, names);
      for (const n of names) scope.names.add(n);
    } else if ((st.type === 'ClassDeclaration' || st.type === 'FunctionDeclaration') && st.id) {
      scope.names.add(st.id.name);
    }
  }
}

// ---------------------------------------------------------------------------
// Reference walker. `ctx.free` accumulates every identifier occurrence that
// resolves to nothing inside the callback -- i.e. a page global.
// ---------------------------------------------------------------------------
function snippet(ctx, node) {
  if (!ctx.src || !node) return null;
  const s = ctx.src.slice(node.start, node.end).replace(/\s+/g, ' ').trim();
  return s.length > 72 ? s.slice(0, 69) + '...' : s;
}

function record(node, scope, ctx, mode) {
  if (resolves(scope, node.name)) return;
  ctx.free.push({ name: node.name, mode, line: node.loc.start.line });
  if (mode === 'write') {
    const ex = snippet(ctx, ctx.site || node);
    if (ex) (ctx.writeExamples[node.name] || (ctx.writeExamples[node.name] = new Set())).add(ex);
  }
}

function unwrapChain(n) { return n && n.type === 'ChainExpression' ? n.expression : n; }

function markPatched(mem, scope, ctx) {
  let n = unwrapChain(mem);
  while (n && n.type === 'MemberExpression') n = unwrapChain(n.object);
  if (!n || n.type !== 'Identifier' || resolves(scope, n.name)) return;
  ctx.patched.add(n.name);
  const ex = snippet(ctx, ctx.site || mem);
  if (ex) (ctx.patchExamples[n.name] || (ctx.patchExamples[n.name] = new Set())).add(ex);
}

function walkFunction(node, parentScope, ctx) {
  const s = newScope(parentScope, 'function');
  if (node.type === 'FunctionExpression' && node.id) s.names.add(node.id.name);
  if (node.type !== 'ArrowFunctionExpression') { s.names.add('arguments'); }
  const pnames = [];
  for (const p of node.params) patternNames(p, pnames);
  for (const n of pnames) s.names.add(n);
  for (const p of node.params) walkPattern(p, s, ctx, true);
  if (node.body.type === 'BlockStatement') {
    hoistVars(node.body, s);
    hoistLexical(node.body.body, s);
    for (const st of node.body.body) walk(st, s, ctx);
  } else {
    walk(node.body, s, ctx);
  }
}

// isBinding: the pattern is a declaration target (names already bound, no ref).
// Otherwise it is an assignment target -> every leaf identifier is a WRITE.
function walkPattern(node, scope, ctx, isBinding) {
  if (!node) return;
  switch (node.type) {
    case 'Identifier':
      if (!isBinding) record(node, scope, ctx, 'write');
      return;
    case 'MemberExpression':
      if (!isBinding) markPatched(node, scope, ctx);
      walk(node, scope, ctx);
      return;
    case 'ObjectPattern':
      for (const p of node.properties) {
        if (p.type === 'RestElement') { walkPattern(p.argument, scope, ctx, isBinding); continue; }
        if (p.computed) walk(p.key, scope, ctx);
        walkPattern(p.value, scope, ctx, isBinding);
      }
      return;
    case 'ArrayPattern':
      for (const e of node.elements) if (e) walkPattern(e, scope, ctx, isBinding);
      return;
    case 'AssignmentPattern':
      walkPattern(node.left, scope, ctx, isBinding);
      walk(node.right, scope, ctx);
      return;
    case 'RestElement': walkPattern(node.argument, scope, ctx, isBinding); return;
    default: walk(node, scope, ctx); return;
  }
}

function declareVariableDeclaration(node, scope, ctx) {
  const target = node.kind === 'var' ? fnScopeOf(scope) || scope : scope;
  for (const d of node.declarations) {
    const names = [];
    patternNames(d.id, names);
    for (const n of names) target.names.add(n);
  }
  for (const d of node.declarations) {
    walkPattern(d.id, scope, ctx, true);
    if (d.init) walk(d.init, scope, ctx);
  }
}

function walk(node, scope, ctx) {
  if (!node) return;
  switch (node.type) {
    case 'Identifier': record(node, scope, ctx, 'read'); return;
    case 'PrivateIdentifier':
    case 'MetaProperty':
    case 'BreakStatement':
    case 'ContinueStatement':
    case 'ImportSpecifier':
    case 'ImportDefaultSpecifier':
    case 'ImportNamespaceSpecifier':
    case 'ExportSpecifier':
    case 'Super':
    case 'ThisExpression':
    case 'Literal':
      return;

    case 'MemberExpression':
      walk(node.object, scope, ctx);
      if (node.computed) walk(node.property, scope, ctx);
      return;

    case 'Property':
    case 'PropertyDefinition':
    case 'MethodDefinition':
      if (node.computed) walk(node.key, scope, ctx);
      walk(node.value, scope, ctx);
      return;

    case 'LabeledStatement': walk(node.body, scope, ctx); return;

    case 'FunctionDeclaration':
    case 'FunctionExpression':
    case 'ArrowFunctionExpression':
      walkFunction(node, scope, ctx);
      return;

    case 'ClassDeclaration':
    case 'ClassExpression': {
      const s = newScope(scope, 'block');
      if (node.id) { s.names.add(node.id.name); if (node.type === 'ClassDeclaration') scope.names.add(node.id.name); }
      if (node.superClass) walk(node.superClass, s, ctx);
      walk(node.body, s, ctx);
      return;
    }

    case 'BlockStatement': {
      const s = newScope(scope, 'block');
      hoistLexical(node.body, s);
      for (const st of node.body) walk(st, s, ctx);
      return;
    }

    case 'SwitchStatement': {
      walk(node.discriminant, scope, ctx);
      const s = newScope(scope, 'block');
      for (const c of node.cases) hoistLexical(c.consequent, s);
      for (const c of node.cases) {
        if (c.test) walk(c.test, s, ctx);
        for (const st of c.consequent) walk(st, s, ctx);
      }
      return;
    }

    case 'ForStatement': {
      const s = newScope(scope, 'block');
      if (node.init) {
        if (node.init.type === 'VariableDeclaration') declareVariableDeclaration(node.init, s, ctx);
        else walk(node.init, s, ctx);
      }
      if (node.test) walk(node.test, s, ctx);
      if (node.update) walk(node.update, s, ctx);
      walk(node.body, s, ctx);
      return;
    }

    case 'ForInStatement':
    case 'ForOfStatement': {
      const s = newScope(scope, 'block');
      if (node.left.type === 'VariableDeclaration') declareVariableDeclaration(node.left, s, ctx);
      else walkPattern(node.left, s, ctx, false);
      walk(node.right, s, ctx);
      walk(node.body, s, ctx);
      return;
    }

    case 'CatchClause': {
      const s = newScope(scope, 'block');
      if (node.param) {
        const names = [];
        patternNames(node.param, names);
        for (const n of names) s.names.add(n);
        walkPattern(node.param, s, ctx, true);
      }
      walk(node.body, s, ctx);
      return;
    }

    case 'VariableDeclaration': declareVariableDeclaration(node, scope, ctx); return;

    case 'AssignmentExpression': {
      const prev = ctx.site;
      ctx.site = node;
      walkPattern(node.left, scope, ctx, false);
      ctx.site = prev;
      walk(node.right, scope, ctx);
      return;
    }

    case 'UpdateExpression': {
      const prev = ctx.site;
      ctx.site = node;
      walkPattern(node.argument, scope, ctx, false);
      ctx.site = prev;
      return;
    }

    case 'UnaryExpression':
      if (node.operator === 'delete' && unwrapChain(node.argument).type === 'MemberExpression') {
        markPatched(node.argument, scope, ctx);
      }
      walk(node.argument, scope, ctx);
      return;

    default:
      eachChild(node, (c) => walk(c, scope, ctx));
  }
}

function analyzeCallback(fnNode, src) {
  const ctx = { free: [], patched: new Set(), src, site: null, writeExamples: {}, patchExamples: {} };
  walkFunction(fnNode, newScope(null, 'program'), ctx);
  return ctx;
}

// ---------------------------------------------------------------------------
// 1. index.html -- inline classic script -> authoritative top-level declarations
// ---------------------------------------------------------------------------
function readAppSurface() {
  const html = fs.readFileSync(APP, 'utf8');
  const decls = new Map(); // name -> {kind, declKind, line, valueIsFunction}
  const scripts = [];

  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    const attrs = m[1] || '';
    if (/\bsrc\s*=/.test(attrs)) continue;
    if (/type\s*=\s*["']?module/i.test(attrs)) { scripts.push({ module: true, attrs }); continue; }
    const body = m[2];
    const startLine = html.slice(0, m.index).split('\n').length;
    const endLine = startLine + body.split('\n').length;
    scripts.push({ module: false, startLine, endLine, chars: body.length });

    const prog = acorn.parse(body, { ecmaVersion: 'latest', sourceType: 'script', locations: true });
    const lineOf = (n) => startLine + n.loc.start.line - 1;

    const put = (name, kind, declKind, node, valueIsFunction) => {
      if (decls.has(name)) return;
      decls.set(name, { kind, declKind, line: lineOf(node), valueIsFunction: !!valueIsFunction });
    };
    const isFnValue = (init) => !!init && (init.type === 'FunctionExpression'
      || init.type === 'ArrowFunctionExpression' || init.type === 'ClassExpression');

    for (const st of prog.body) {
      if (st.type === 'FunctionDeclaration' && st.id) put(st.id.name, 'function', 'function', st, true);
      else if (st.type === 'ClassDeclaration' && st.id) put(st.id.name, 'class', 'class', st, true);
      else if (st.type === 'VariableDeclaration') {
        const kind = st.kind === 'const' ? 'const-global' : 'mutable-global';
        for (const d of st.declarations) {
          const names = [];
          patternNames(d.id, names);
          for (const n of names) put(n, kind, st.kind, d, isFnValue(d.init));
        }
      }
    }
    // var / function declarations nested in top-level blocks (if/try/for) are
    // still hoisted globals.
    const hoisted = newScope(null, 'program');
    hoistVars(prog, hoisted);
    walkAll(prog, (n) => {
      if (n.type === 'FunctionDeclaration' && n.id && !decls.has(n.id.name) && hoisted.names.has(n.id.name)) {
        put(n.id.name, 'function', 'function-hoisted', n, true);
      }
      if (n.type === 'VariableDeclaration' && n.kind === 'var') {
        for (const d of n.declarations) {
          const names = [];
          patternNames(d.id, names);
          for (const x of names) {
            if (!decls.has(x) && hoisted.names.has(x)) put(x, 'mutable-global', 'var-hoisted', d, isFnValue(d.init));
          }
        }
      }
    });
  }

  // Element ids -> implicit window globals (browser-provided, never bridged).
  const domIds = new Set();
  const ident = /^[A-Za-z_$][A-Za-z0-9_$]*$/;
  for (const rx of [/\bid\s*=\s*"([^"${}]+)"/g, /\bid\s*=\s*'([^'${}]+)'/g, /\.id\s*=\s*['"]([^'"${}]+)['"]/g]) {
    let mm;
    while ((mm = rx.exec(html)) !== null) if (ident.test(mm[1])) domIds.add(mm[1]);
  }

  return { decls, domIds, scripts };
}

// ---------------------------------------------------------------------------
// 2. Test scripts -> every page-side callback -> free identifiers
// ---------------------------------------------------------------------------
function readTestSurface() {
  const files = fs.readdirSync(DIR)
    .filter((f) => /^_(?:verify|diag)[A-Za-z0-9_]*\.js$/.test(f) && f !== SELF)
    .sort();

  const usage = new Map(); // name -> {reads, writes, refCount, files:Set, patchedIn:Set, writtenIn:Set}
  const perFile = [];
  const parseErrors = [];
  const unresolvedSites = []; // page-side calls whose body we could not parse
  const windowProps = new Map(); // window.X seen in a page-side callback
  let callbackCount = 0;
  let indirectCount = 0;

  const bump = (name) => {
    let u = usage.get(name);
    if (!u) {
      u = {
        refCount: 0, reads: 0, writes: 0, files: new Set(),
        writtenIn: new Set(), patchedIn: new Set(),
        writeExamples: new Set(), patchExamples: new Set(),
      };
      usage.set(name, u);
    }
    return u;
  };

  for (const file of files) {
    const src = fs.readFileSync(path.join(DIR, file), 'utf8');
    let prog;
    try {
      prog = acorn.parse(src, {
        ecmaVersion: 'latest', sourceType: 'script', locations: true,
        allowReturnOutsideFunction: true, allowAwaitOutsideFunction: true,
      });
    } catch (e) {
      parseErrors.push({ file, error: e.message });
      continue;
    }

    // Node-side function bindings, so `page.evaluate(installHarness, arg)` -- a
    // function DECLARED IN NODE and serialized into the page -- is analysed too.
    // Missing this pattern would silently drop a whole harness worth of globals.
    const nodeFns = new Map();
    walkAll(prog, (n) => {
      if (n.type === 'FunctionDeclaration' && n.id) nodeFns.set(n.id.name, n);
      else if (n.type === 'VariableDeclarator' && n.id.type === 'Identifier' && n.init
        && (n.init.type === 'FunctionExpression' || n.init.type === 'ArrowFunctionExpression')) {
        nodeFns.set(n.id.name, n.init);
      }
    });

    let cbs = 0;
    const seen = new Set();
    walkAll(prog, (n) => {
      if (n.type !== 'CallExpression') return;
      const callee = unwrapChain(n.callee);
      if (!callee || callee.type !== 'MemberExpression' || callee.computed) return;
      if (callee.property.type !== 'Identifier' || !PAGE_SIDE.has(callee.property.name)) return;

      let fn = n.arguments.find((a) => a && (a.type === 'ArrowFunctionExpression'
        || a.type === 'FunctionExpression'));
      let indirect = false;
      if (!fn) {
        const byName = n.arguments.find((a) => a && a.type === 'Identifier' && nodeFns.has(a.name));
        if (byName) { fn = nodeFns.get(byName.name); indirect = true; }
      }
      if (!fn) {
        // waitForFunction/evaluate also accept a string body or a JSHandle. Record
        // it so nothing is skipped without a trace.
        unresolvedSites.push({
          file,
          line: n.loc.start.line,
          method: callee.property.name,
          argKinds: n.arguments.map((a) => (a ? a.type : 'null')),
        });
        return;
      }
      if (seen.has(fn)) return;
      seen.add(fn);
      cbs += 1;
      callbackCount += 1;
      if (indirect) indirectCount += 1;

      walkAll(fn, (w) => {
        if (w.type === 'MemberExpression' && !w.computed && w.object.type === 'Identifier'
          && w.object.name === 'window' && w.property.type === 'Identifier') {
          const list = windowProps.get(w.property.name) || new Set();
          list.add(file);
          windowProps.set(w.property.name, list);
        }
      });

      const ctx = analyzeCallback(fn, src);
      for (const [name, set] of Object.entries(ctx.writeExamples)) {
        const u = bump(name);
        for (const ex of set) u.writeExamples.add(ex);
      }
      for (const [name, set] of Object.entries(ctx.patchExamples)) {
        const u = bump(name);
        for (const ex of set) u.patchExamples.add(ex);
      }
      const local = new Map();
      for (const ref of ctx.free) {
        let e = local.get(ref.name);
        if (!e) { e = { reads: 0, writes: 0 }; local.set(ref.name, e); }
        if (ref.mode === 'write') e.writes += 1; else e.reads += 1;
      }
      for (const [name, e] of local) {
        const u = bump(name);
        u.refCount += e.reads + e.writes;
        u.reads += e.reads;
        u.writes += e.writes;
        u.files.add(file);
        if (e.writes) u.writtenIn.add(file);
      }
      for (const name of ctx.patched) {
        const u = bump(name);
        if (!u.files.has(name)) u.files.add(file);
        u.patchedIn.add(file);
      }
    });
    perFile.push({ file, callbacks: cbs });
  }

  return { files, usage, perFile, parseErrors, callbackCount, indirectCount, unresolvedSites, windowProps };
}

// ---------------------------------------------------------------------------
// 3. Classify + emit
// ---------------------------------------------------------------------------
function main() {
  const app = readAppSurface();
  const tests = readTestSurface();

  const symbols = [];
  const unknown = [];
  const builtinsHit = [];
  const domIdCollisions = [];

  // window.X inside a page-side callback: reads an app global through window
  // (bridge-safe, since the bridge writes to window) vs a value the test itself
  // installed on window (not part of the app surface at all).
  const windowAccess = [...tests.windowProps.entries()]
    .map(([prop, fset]) => ({
      prop,
      appGlobal: app.decls.has(prop),
      files: [...fset].sort(),
    }))
    .sort((a, b) => a.prop.localeCompare(b.prop));

  for (const [name, u] of tests.usage) {
    const decl = app.decls.get(name);
    const isId = app.domIds.has(name);
    let kind;
    let entry = {
      name,
      kind: null,
      written: u.writes > 0,
      patched: u.patchedIn.size > 0,
      refCount: u.refCount,
      fileCount: u.files.size,
      files: [...u.files].sort(),
    };

    if (decl) {
      kind = decl.kind;
      entry.declKind = decl.declKind;
      entry.declLine = decl.line;
      if (decl.valueIsFunction) entry.valueIsFunction = true;
      if (isId) domIdCollisions.push(name);
    } else if (isId) {
      kind = 'dom-id';
    } else if (isBuiltin(name)) {
      builtinsHit.push(name);
      continue; // not part of the bridge surface
    } else {
      kind = 'unknown';
      unknown.push({ name, refCount: u.refCount, files: entry.files });
    }
    entry.kind = kind;
    if (u.writes) {
      entry.writeFiles = [...u.writtenIn].sort();
      entry.writeExamples = [...u.writeExamples].sort().slice(0, 4);
    }
    if (u.patchedIn.size) {
      entry.patchFiles = [...u.patchedIn].sort();
      entry.patchExamples = [...u.patchExamples].sort().slice(0, 4);
    }
    entry.reads = u.reads;
    entry.writes = u.writes;
    symbols.push(entry);
  }

  symbols.sort((a, b) => (b.refCount - a.refCount) || a.name.localeCompare(b.name));

  const byKind = {};
  for (const s of symbols) byKind[s.kind] = (byKind[s.kind] || 0) + 1;
  const bridged = symbols.filter((s) => s.kind !== 'dom-id' && s.kind !== 'unknown');

  const out = {
    meta: {
      purpose: 'Frozen contract: the exact page-global surface the _verify_* suite '
        + 'reaches into. A test bridge for the ES-module build must re-expose every '
        + 'symbol below whose kind is not "dom-id".',
      generator: SELF,
      method: 'acorn AST parse + scope walker (exact); no regex identifier scanning',
      acornVersion: (() => { try { return require('acorn/package.json').version; } catch (_) { return 'unknown'; } })(),
      deterministic: true,
      app: {
        file: 'index.html',
        inlineClassicScripts: app.scripts.filter((s) => !s.module).length,
        moduleScripts: app.scripts.filter((s) => s.module).length,
        scriptLines: app.scripts.filter((s) => !s.module)
          .map((s) => `${s.startLine}-${s.endLine}`).join(','),
        topLevelDeclarations: app.decls.size,
        elementIds: app.domIds.size,
      },
      tests: {
        files: tests.files.length,
        fileList: tests.files,
        pageSideCallbacks: tests.callbackCount,
        indirectCallbacks: tests.indirectCount,
        methodsScanned: [...PAGE_SIDE].sort(),
        parseErrors: tests.parseErrors,
        unresolvedCallSites: tests.unresolvedSites,
        windowPropertyAccess: windowAccess,
      },
      caveats: [
        'refCount counts identifier occurrences across all page-side callbacks; '
          + 'fileCount counts distinct test files.',
        '"written" means the symbol is the target of an assignment or ++/-- inside a '
          + 'page-side callback -> the bridge needs a SETTER, not just a getter.',
        '"patched" means a property was assigned through the symbol (e.g. gl.bindBuffer=, '
          + 'TYPES.blur.eval=) -> the bridge must expose the LIVE object, never a copy.',
        'Identifiers declared at index.html top level always win over the builtin '
          + 'deny-list, so app globals that shadow a DOM name (e.g. GPU) are never lost.',
        'Page-side callbacks passed by NAME (page.evaluate(installHarness, arg)) are '
          + 'resolved to their Node-side declaration and analysed like inline ones.',
        'meta.tests.unresolvedCallSites lists page-side calls with no analysable '
          + 'function argument (string bodies, handles). It must stay empty, or the '
          + 'surface is incomplete.',
        'meta.tests.windowPropertyAccess lists every window.X touched from a page-side '
          + 'callback, flagged with whether X is an index.html global.',
      ],
    },
    summary: {
      totalSymbols: symbols.length,
      needsBridge: bridged.length,
      byKind,
      written: symbols.filter((s) => s.written).length,
      patched: symbols.filter((s) => s.patched).length,
      writtenNeedingBridge: bridged.filter((s) => s.written).length,
      patchedNeedingBridge: bridged.filter((s) => s.patched).length,
      unknown: unknown.length,
      builtinsFiltered: [...new Set(builtinsHit)].sort().length,
    },
    unknown: unknown.sort((a, b) => b.refCount - a.refCount),
    domIdCollisions: [...new Set(domIdCollisions)].sort(),
    builtinsFiltered: [...new Set(builtinsHit)].sort(),
    symbols,
  };

  const json = JSON.stringify(out, null, 2) + '\n';
  const CHECK = process.argv.slice(2).includes('--check');
  if (!CHECK) fs.writeFileSync(OUT, json);

  // ---- console report ----
  const pad = (s, n) => String(s).padEnd(n);
  console.log(`bridge surface -> ${path.relative(DIR, OUT)}`);
  console.log(`  app        : index.html, ${out.meta.app.inlineClassicScripts} inline classic script(s) `
    + `(lines ${out.meta.app.scriptLines}), ${out.meta.app.topLevelDeclarations} top-level decls, `
    + `${out.meta.app.elementIds} element ids`);
  console.log(`  tests      : ${tests.files.length} files, ${tests.callbackCount} page-side callbacks `
    + `(${tests.indirectCount} passed by name)`);
  console.log(`  method     : ${out.meta.method}`);
  console.log('');
  console.log(`  symbols    : ${out.summary.totalSymbols} (bridge must expose ${out.summary.needsBridge})`);
  for (const k of Object.keys(byKind).sort()) console.log(`      ${pad(k, 16)} ${byKind[k]}`);
  console.log(`  written    : ${out.summary.written}  (needs a setter)`);
  console.log(`  patched    : ${out.summary.patched}  (needs the live object)`);
  console.log(`  unknown    : ${out.summary.unknown}`);
  if (tests.parseErrors.length) {
    console.log('\n  !! PARSE ERRORS');
    for (const e of tests.parseErrors) console.log(`      ${e.file}: ${e.error}`);
  }
  if (unknown.length) {
    console.log('\n  !! UNKNOWN (referenced by a test, not declared in index.html, not a known builtin)');
    for (const u of out.unknown) console.log(`      ${pad(u.name, 24)} x${pad(u.refCount, 4)} ${u.files.join(' ')}`);
  }
  if (tests.unresolvedSites.length) {
    console.log('\n  !! PAGE-SIDE CALLS WITH NO ANALYSABLE FUNCTION ARGUMENT');
    for (const s of tests.unresolvedSites) {
      console.log(`      ${s.file}:${s.line} .${s.method}(${s.argKinds.join(', ')})`);
    }
  }
  const winApp = windowAccess.filter((w) => w.appGlobal);
  if (winApp.length) {
    console.log('\n  note: app globals also reached via window.X: '
      + winApp.map((w) => w.prop).join(', '));
  }
  if (out.domIdCollisions.length) {
    console.log('\n  note: also an element id (script declaration wins): ' + out.domIdCollisions.join(', '));
  }
  console.log('\n  top 20 by reference count');
  for (const s of symbols.slice(0, 20)) {
    const flags = [s.written ? 'W' : ' ', s.patched ? 'P' : ' '].join('');
    console.log(`      ${pad(s.name, 22)} ${pad(s.kind, 15)} ${flags} refs=${pad(s.refCount, 5)} files=${s.fileCount}`);
  }

  if (!CHECK) {
    console.log(`\n  wrote ${path.relative(DIR, OUT)}. Gate a later commit with: node ${SELF} --check`);
    return;
  }

  // ---- --check: mechanical diff against the frozen contract ----
  let frozen;
  try { frozen = JSON.parse(fs.readFileSync(OUT, 'utf8')); } catch (e) {
    console.error(`\nFAIL: cannot read ${path.basename(OUT)}: ${e.message}`);
    process.exit(1);
  }
  const was = new Map(frozen.symbols.map((s) => [s.name, s]));
  const now = new Map(symbols.map((s) => [s.name, s]));
  const drift = [];
  for (const [name, s] of now) {
    const o = was.get(name);
    if (!o) { drift.push(`+ ADDED    ${name} (${s.kind})`); continue; }
    if (o.kind !== s.kind) drift.push(`~ KIND     ${name}: ${o.kind} -> ${s.kind}`);
    if (o.written !== s.written) drift.push(`~ WRITTEN  ${name}: ${o.written} -> ${s.written}`);
    if (o.patched !== s.patched) drift.push(`~ PATCHED  ${name}: ${o.patched} -> ${s.patched}`);
  }
  for (const name of was.keys()) {
    if (!now.has(name)) drift.push(`- REMOVED  ${name} (${was.get(name).kind}) -- the bridge no longer needs it`);
  }
  const hard = tests.parseErrors.length + tests.unresolvedSites.length + unknown.length;
  console.log('');
  if (!drift.length && !hard) {
    console.log(`  PASS: live surface matches ${path.basename(OUT)} (${symbols.length} symbols).`);
    return;
  }
  if (drift.length) {
    console.log(`  FAIL: ${drift.length} change(s) vs ${path.basename(OUT)}`);
    for (const d of drift.sort()) console.log('      ' + d);
    console.log(`\n  If intentional, re-freeze with: node ${SELF}`);
  }
  if (hard) console.log(`  FAIL: ${hard} extraction problem(s) reported above.`);
  process.exit(1);
}

main();
