// Refuse any plugin that touches a legacy binding at MODULE-EVALUATION time.
//
// THE FAILURE THIS CATCHES. legacy.js imports the plugins; the plugins import back from legacy.js.
// In that cycle the PLUGIN evaluates first, as a dependency, while every legacy binding is still in
// its temporal dead zone. So the two halves of a plugin behave completely differently:
//
//   params: [P.curve("skirt", "Skirt", mountainSkirtDefault())]   <- runs NOW. TDZ. Throws.
//   eval:   (p, ins) => blendField(...)                            <- runs LATER. Safe.
//
// It is not a subtle failure when it fires - "Cannot access X before initialization", the whole
// module graph fails to load, the page is blank. But it is invisible to everything cheaper than
// loading the page: the modules parse, the imports link, and `vite build` SUCCEEDS, because
// bundling flattens the graph into one scope where hoisting resolves what native ESM will not.
// That gap is the reason this check exists as its own gate rather than as a build step.
//
// The fix is never to defer the reference - it is to move the thing being referenced OUT of the
// cycle, into src/core/, where it can be read at any time.
const fs = require('fs');
const path = require('path');
const acorn = require('acorn');
const walk = require('acorn-walk');

const APP = path.resolve(__dirname, '..');
const PLUGINS = path.join(APP, 'src', 'plugins');

if (!fs.existsSync(PLUGINS)) { console.log('no plugins yet — nothing to check'); process.exit(0); }

const files = [];
const collect = (dir) => {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) collect(p);
    else if (e.name.endsWith('.js') && e.name !== 'index.js') files.push(p);
  }
};
collect(PLUGINS);

let violations = 0;
let checked = 0;

for (const file of files) {
  const src = fs.readFileSync(file, 'utf8');
  const ast = acorn.parse(src, { ecmaVersion: 2022, sourceType: 'module', locations: true });

  // names imported from legacy.js — the ones that are in TDZ during our evaluation
  const cyclic = new Set();
  for (const n of ast.body) {
    if (n.type !== 'ImportDeclaration') continue;
    if (!/legacy\.js$/.test(n.source.value)) continue;
    for (const s of n.specifiers) cyclic.add(s.local.name);
  }
  if (!cyclic.size) { checked++; continue; }

  // Walk everything NOT inside a function body. Anything reached is evaluated at module load.
  let depth = 0;
  const hits = [];
  walk.recursive(ast, null, {
    Function() { /* do not descend — a closure body runs later, which is the whole point */ },
    MemberExpression(node, st, c) { c(node.object, st); if (node.computed) c(node.property, st); },
    Property(node, st, c) { if (node.computed) c(node.key, st); c(node.value, st); },
    ImportDeclaration() { /* the import itself is not a reference */ },
    Identifier(node) {
      if (cyclic.has(node.name)) hits.push({ name: node.name, line: node.loc.start.line });
    },
  });

  checked++;
  if (hits.length) {
    violations += hits.length;
    console.log(`\n  ${path.relative(APP, file)}`);
    for (const h of hits) {
      console.log(`    TDZ  ${h.name} referenced at line ${h.line} OUTSIDE any function`);
    }
  }
}

console.log(`\n  checked ${checked} plugin module(s)`);
if (violations) {
  console.log(`  ${violations} module-evaluation-time reference(s) into the legacy cycle.`);
  console.log('  Each will throw "Cannot access X before initialization" and blank the page.');
  console.log('  Fix by moving the referenced binding into src/core/, not by deferring the read.');
  process.exit(1);
}
console.log('  no plugin touches a legacy binding at module-evaluation time');
