// Every identifier a plugin references must resolve to something: a local, an import, or a builtin.
//
// THE FAILURE THIS CATCHES. The extractor decides what to import by comparing the entry's
// identifiers against legacy's top-level declarations. If that declaration list is incomplete, the
// name is never recognised as legacy's, no import is generated, and the node dies at eval with
// "X is not defined" — a runtime failure from a static mistake.
//
// It has already happened once, and the cause is worth remembering: the declaration list was built
// by matching line starts, which reads only the FIRST name of a multi-declarator statement.
// `export const TEMP_MIN_C=-100,TEMP_MAX_C=1400,FIELD_META=new WeakMap();` contributed one name of
// three, and 68 of legacy's 475 top-level declarations — 14% — were invisible. d_heat happened to
// be the node that tripped it; the other 67 were simply not referenced yet.
//
// So this checks the RESULT rather than trusting the process. The extractor was fixed to parse
// instead of match, but a generator that is correct today is not a guarantee about the files on
// disk, and these files are edited by hand afterwards.
const fs = require('fs')
const path = require('path')
const acorn = require('acorn')
const walk = require('acorn-walk')

const APP = path.resolve(__dirname, '..')
const PLUGINS = path.join(APP, 'src', 'plugins')
if (!fs.existsSync(PLUGINS)) { console.log('no plugins yet'); process.exit(0) }

const BUILTINS = new Set(['undefined', 'NaN', 'Infinity', 'globalThis', 'console', 'Math', 'Number',
  'String', 'Object', 'Array', 'JSON', 'Promise', 'Set', 'Map', 'WeakMap', 'WeakSet', 'Date', 'Error',
  'TypeError', 'RangeError', 'isNaN', 'isFinite', 'parseInt', 'parseFloat', 'Float32Array',
  'Float64Array', 'Uint8Array', 'Uint16Array', 'Uint32Array', 'Int32Array', 'Uint8ClampedArray',
  'ArrayBuffer', 'DataView', 'performance', 'document', 'window', 'navigator', 'setTimeout',
  'clearTimeout', 'setInterval', 'clearInterval', 'requestAnimationFrame', 'Image', 'fetch',
  'structuredClone', 'Boolean', 'Symbol', 'BigInt', 'RegExp', 'Function', 'Intl', 'URL', 'Blob'])

const files = []
const collect = (dir) => {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) collect(p)
    else if (e.name.endsWith('.js') && e.name !== 'index.js') files.push(p)
  }
}
collect(PLUGINS)

let unresolved = 0
let checked = 0

for (const file of files) {
  const src = fs.readFileSync(file, 'utf8')
  const ast = acorn.parse(src, { ecmaVersion: 2022, sourceType: 'module', locations: true })

  const known = new Set(BUILTINS)
  for (const n of ast.body) {
    if (n.type === 'ImportDeclaration') for (const s of n.specifiers) known.add(s.local.name)
    const d = n.type === 'ExportNamedDeclaration' || n.type === 'ExportDefaultDeclaration' ? n.declaration : n
    if (!d) continue
    if ((d.type === 'FunctionDeclaration' || d.type === 'ClassDeclaration') && d.id) known.add(d.id.name)
    if (d.type === 'VariableDeclaration') for (const v of d.declarations) if (v.id.type === 'Identifier') known.add(v.id.name)
  }

  const scopes = [new Set()]
  const free = new Map()
  walk.recursive(ast, null, {
    Function(node, st, c) {
      const s = new Set()
      if (node.id) s.add(node.id.name)
      const bind = (p) => {
        if (!p) return
        if (p.type === 'Identifier') s.add(p.name)
        else if (p.type === 'ObjectPattern') p.properties.forEach((q) => bind(q.value || q.argument))
        else if (p.type === 'ArrayPattern') p.elements.forEach((x) => x && bind(x))
        else if (p.type === 'AssignmentPattern') bind(p.left)
        else if (p.type === 'RestElement') bind(p.argument)
      }
      node.params.forEach(bind)
      scopes.push(s); c(node.body, st); scopes.pop()
    },
    BlockStatement(node, st, c) {
      const s = new Set()
      for (const b of node.body) {
        if (b.type === 'FunctionDeclaration' && b.id) s.add(b.id.name)
        if (b.type === 'ClassDeclaration' && b.id) s.add(b.id.name)
        if (b.type === 'VariableDeclaration') for (const v of b.declarations) if (v.id.type === 'Identifier') s.add(v.id.name)
      }
      scopes.push(s); node.body.forEach((b) => c(b, st)); scopes.pop()
    },
    ForStatement(node, st, c) {
      const s = new Set()
      if (node.init && node.init.type === 'VariableDeclaration') {
        for (const v of node.init.declarations) if (v.id.type === 'Identifier') s.add(v.id.name)
      }
      scopes.push(s)
      if (node.init) c(node.init, st); if (node.test) c(node.test, st)
      if (node.update) c(node.update, st); c(node.body, st)
      scopes.pop()
    },
    ForOfStatement(node, st, c) {
      const s = new Set()
      if (node.left.type === 'VariableDeclaration') for (const v of node.left.declarations) if (v.id.type === 'Identifier') s.add(v.id.name)
      scopes.push(s); c(node.left, st); c(node.right, st); c(node.body, st); scopes.pop()
    },
    ForInStatement(node, st, c) {
      const s = new Set()
      if (node.left.type === 'VariableDeclaration') for (const v of node.left.declarations) if (v.id.type === 'Identifier') s.add(v.id.name)
      scopes.push(s); c(node.left, st); c(node.right, st); c(node.body, st); scopes.pop()
    },
    CatchClause(node, st, c) {
      const s = new Set()
      if (node.param && node.param.type === 'Identifier') s.add(node.param.name)
      scopes.push(s); c(node.body, st); scopes.pop()
    },
    MemberExpression(node, st, c) { c(node.object, st); if (node.computed) c(node.property, st) },
    Property(node, st, c) { if (node.computed) c(node.key, st); c(node.value, st) },
    ImportDeclaration() {},
    Identifier(node) {
      const n = node.name
      if (known.has(n) || scopes.some((s) => s.has(n))) return
      if (!free.has(n)) free.set(n, node.loc.start.line)
    },
  })

  checked++
  if (free.size) {
    unresolved += free.size
    console.log(`\n  ${path.relative(APP, file)}`)
    for (const [n, line] of [...free.entries()].sort((a, b) => a[1] - b[1])) {
      console.log(`    UNRESOLVED  ${n.padEnd(24)} line ${line}`)
    }
  }
}

console.log(`\n  checked ${checked} plugin module(s)`)
if (unresolved) {
  console.log(`  ${unresolved} identifier(s) resolve to nothing — each is a "X is not defined" at eval time.`)
  process.exit(1)
}
console.log('  every identifier resolves to a local, an import or a builtin')
