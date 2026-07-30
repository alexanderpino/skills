// Phase B: move one category of node types out of TYPES into src/plugins/<cat>/.
//
//   node extract_cat.js <cat>
//
// Entries are located and cut by BRACE MATCHING from their `  key:{cat:"<cat>"` line, never by line
// number, and the body is moved verbatim — the digest is a byte-identity gate, so a reformat is
// indistinguishable from a behaviour change until it fails.
//
// Two traps this script exists to not repeat:
//   * brace matching stops at the `}`, but slicing whole LINES drags in the `,` that separates
//     entries in the object literal — that produced six unbalanced files on the first run.
//   * the second and later batches must NOT re-wrap TYPES in mergePlugins(); it is already wrapped.
const fs = require('fs');
const path = require('path');
const acorn = require('acorn');
const walk = require('acorn-walk');

const CAT = process.argv[2];
if (!CAT) { console.error('usage: extract_cat.js <cat>'); process.exit(2); }

const APP = path.resolve(__dirname, '..');   // the app dir, wherever the checkout lives
const LEGACY = path.join(APP, 'src', 'legacy.js');
const OUT = path.join(APP, 'src', 'plugins', CAT);

const lines = fs.readFileSync(LEGACY, 'utf8').split('\n');

const starts = [];
for (let i = 0; i < lines.length; i++) {
  const m = lines[i].match(new RegExp(`^  ([a-zA-Z_][a-zA-Z0-9_]*):\\{cat:"${CAT}"`));
  if (m) starts.push({ key: m[1], line: i });
}
if (!starts.length) { console.error(`no ${CAT} entries found`); process.exit(1); }

const entries = starts.map(({ key, line }) => {
  let d = 0, started = false, end = line;
  for (let i = line; i < lines.length; i++) {
    for (const ch of lines[i]) { if (ch === '{') { d++; started = true; } else if (ch === '}') d--; }
    if (started && d === 0) { end = i; break; }
  }
  const text = lines.slice(line, end + 1).join('\n').replace(/,\s*$/, '');
  return { key, line, end, text };
});

console.log(`  ${CAT}: ${entries.length} entries — ${entries.map((e) => e.key).join(' ')}`);

const legacyDecls = new Set();
for (const l of lines) {
  const m = l.match(/^(?:export )?(?:function|const|let|var)\s+([a-zA-Z_$][\w$]*)/);
  if (m) legacyDecls.add(m[1]);
}

fs.mkdirSync(OUT, { recursive: true });

for (const e of entries) {
  const inner = e.text.replace(new RegExp(`^  ${e.key}:\\{`), '{');
  const body = `{\n  type: ${JSON.stringify(e.key)},\n` + inner.slice(1);

  // Every identifier the entry actually REFERENCES, found by parsing rather than by pattern.
  //
  // A regex over the text is wrong here and was: it matched `select` inside name:"Height select"
  // and desc:"Slope select", so three mask plugins imported a UI function they never call, and
  // legacy.js had to export it to satisfy them. Over 60 nodes that would have dragged a large part
  // of the UI surface into the plugin layer for no reason.
  //
  // Parsing the entry as an expression fixes it precisely: non-computed property KEYS are skipped
  // (so `blur:` is not a reference to the blur function), string contents are not identifiers at
  // all, and locally-bound names (arrow params like `p`, `ins`, `nd`) resolve to themselves.
  const used = new Set();
  {
    // `inner`, not `e.text` — the latter still carries the `  key:` prefix from the object literal,
    // which is not a valid expression on its own.
    const expr = acorn.parseExpressionAt(`(${inner})`, 0, { ecmaVersion: 2022 });
    const bound = [new Set()];
    walk.recursive(expr, null, {
      Function(node, st, c) {
        const s = new Set();
        if (node.id) s.add(node.id.name);
        node.params.forEach(function collect(p) {
          if (!p) return;
          if (p.type === 'Identifier') s.add(p.name);
          else if (p.type === 'ObjectPattern') p.properties.forEach((q) => collect(q.value || q.argument));
          else if (p.type === 'ArrayPattern') p.elements.forEach((x) => x && collect(x));
          else if (p.type === 'AssignmentPattern') collect(p.left);
          else if (p.type === 'RestElement') collect(p.argument);
        });
        bound.push(s); c(node.body, st); bound.pop();
      },
      MemberExpression(node, st, c) { c(node.object, st); if (node.computed) c(node.property, st); },
      Property(node, st, c) { if (node.computed) c(node.key, st); c(node.value, st); },
      Identifier(node) {
        if (bound.some((s) => s.has(node.name))) return;
        if (legacyDecls.has(node.name)) used.add(node.name);
      },
    });
  }
  for (const n of ['P', 'WHEN', 'GROUP', 'CAT', 'definePlugin']) used.delete(n);

  const needsP = /\bP\./.test(e.text);
  const needsWHEN = /\bWHEN\(/.test(e.text);
  const needsGROUP = /\bGROUP\(/.test(e.text);
  const paramImports = [needsP && 'P', needsWHEN && 'WHEN', needsGROUP && 'GROUP'].filter(Boolean);

  const imports = [
    `import { definePlugin } from '../../core/registry.js'`,
    paramImports.length ? `import { ${paramImports.join(', ')} } from '../../core/params.js'` : null,
    used.size ? `import { ${[...used].sort().join(', ')} } from '../../legacy.js'` : null,
  ].filter(Boolean).join('\n') + '\n';

  const note = used.size
    ? '//\n// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run\n'
      + '// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at\n'
      + '// module-evaluation time (the params array) comes from core/params.js, outside the cycle.\n'
    : '';

  const desc = (e.text.match(/desc:"([^"]{0,90})/) || [, `${CAT} node.`])[1];
  const file = `// ${e.key} — ${desc}\n${note}` + imports + '\n'
    + `export default definePlugin(${body})\n`;

  fs.writeFileSync(path.join(OUT, `${e.key}.js`), file, 'utf8');
}

const index = `// Every ${CAT} plugin. Imported for the side effect of registering with core/registry.js.\n`
  + entries.map((e) => `import './${e.key}.js'`).join('\n') + '\n';
fs.writeFileSync(path.join(OUT, 'index.js'), index, 'utf8');

let out = lines.slice();
for (const e of [...entries].sort((a, b) => b.line - a.line)) out.splice(e.line, e.end - e.line + 1);
let legacy = out.join('\n');

const importLine = `import './plugins/${CAT}/index.js';`;
if (!legacy.includes(importLine)) {
  legacy = legacy.replace(/^(import \{ mergePlugins \}[^\n]*\n)/m, `$1${importLine}\n`);
}

if (!/^const TYPES=mergePlugins\(\{/m.test(legacy)) {
  const ls = legacy.split('\n');
  const tStart = ls.findIndex((l) => l.startsWith('const TYPES={'));
  let d = 0, started = false, tEnd = tStart;
  for (let i = tStart; i < ls.length; i++) {
    for (const ch of ls[i]) { if (ch === '{') { d++; started = true; } else if (ch === '}') d--; }
    if (started && d === 0) { tEnd = i; break; }
  }
  ls[tStart] = ls[tStart].replace('const TYPES={', 'const TYPES=mergePlugins({');
  ls[tEnd] = ls[tEnd].replace(/\};?\s*$/, '});');
  legacy = ls.join('\n');
}

fs.writeFileSync(LEGACY, legacy, 'utf8');
console.log(`  wrote ${entries.length} module(s) + index.js to src/plugins/${CAT}/`);
console.log(`  legacy.js: ${lines.length} -> ${legacy.split('\n').length} lines`);
