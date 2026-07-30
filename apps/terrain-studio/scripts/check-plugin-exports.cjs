// Every name a plugin imports must actually be EXPORTED by the module it imports from.
//
// The complement to check-plugin-imports.cjs, and they catch opposite mistakes:
//   imports  — a name is referenced but imported from nowhere  -> "X is not defined" at eval
//   exports  — a name is imported but the source does not export it -> the whole graph fails to
//              link, and the page is blank with a message about one symbol
//
// Both are needed because a fix for one can create the other. Adding imports to satisfy the first
// check is exactly how `Math`, `console` and a loop variable `i` ended up in a legacy import list:
// the scope walk that generated them was weaker than the one that verified them, so builtins and
// locals were mistaken for missing imports. This gate makes that impossible to leave behind.
//
//   --fix   remove imported names the source does not export
const fs = require('fs')
const path = require('path')
const acorn = require('acorn')

const APP = path.resolve(__dirname, '..')
const PLUGINS = path.join(APP, 'src', 'plugins')
const FIX = process.argv.includes('--fix')
if (!fs.existsSync(PLUGINS)) { console.log('no plugins yet'); process.exit(0) }

const exportsOf = (file) => {
  const out = new Set()
  if (!fs.existsSync(file)) return out
  const ast = acorn.parse(fs.readFileSync(file, 'utf8'), { ecmaVersion: 2022, sourceType: 'module' })
  for (const n of ast.body) {
    if (n.type === 'ExportNamedDeclaration') {
      if (n.declaration) {
        const d = n.declaration
        if ((d.type === 'FunctionDeclaration' || d.type === 'ClassDeclaration') && d.id) out.add(d.id.name)
        if (d.type === 'VariableDeclaration') for (const v of d.declarations) if (v.id.type === 'Identifier') out.add(v.id.name)
      }
      for (const s of n.specifiers || []) out.add(s.exported.name)
    }
  }
  return out
}

const cache = new Map()
const exportsFor = (abs) => {
  if (!cache.has(abs)) cache.set(abs, exportsOf(abs))
  return cache.get(abs)
}

const files = []
const collect = (dir) => {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) collect(p)
    else if (e.name.endsWith('.js') && e.name !== 'index.js') files.push(p)
  }
}
collect(PLUGINS)

let bad = 0, fixed = 0, checked = 0
for (const file of files) {
  let src = fs.readFileSync(file, 'utf8')
  const ast = acorn.parse(src, { ecmaVersion: 2022, sourceType: 'module', locations: true })
  const problems = []

  for (const n of ast.body) {
    if (n.type !== 'ImportDeclaration') continue
    const abs = path.resolve(path.dirname(file), n.source.value)
    const ex = exportsFor(abs)
    if (!ex.size) continue                      // unreadable or side-effect import; not our business
    for (const s of n.specifiers) {
      if (s.type !== 'ImportSpecifier') continue
      if (!ex.has(s.imported.name)) problems.push({ name: s.imported.name, from: n.source.value, line: s.loc.start.line })
    }
  }

  checked++
  if (!problems.length) continue
  bad += problems.length
  console.log(`\n  ${path.relative(APP, file)}`)
  for (const p of problems) console.log(`    NOT EXPORTED  ${p.name.padEnd(20)} by ${p.from}  (line ${p.line})`)

  if (FIX) {
    for (const p of problems) {
      const re = new RegExp(`(import \\{[^}]*\\} from '${p.from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}')`)
      src = src.replace(re, (whole) => {
        const names = whole.match(/\{([^}]*)\}/)[1].split(',').map((s) => s.trim())
          .filter((s) => s && s !== p.name)
        return names.length ? whole.replace(/\{[^}]*\}/, `{ ${names.join(', ')} }`) : ''
      })
    }
    src = src.replace(/^\s*\n(?=import)/gm, '')
    fs.writeFileSync(file, src, 'utf8')
    fixed += problems.length
  }
}

console.log(`\n  checked ${checked} plugin module(s)`)
if (FIX && fixed) { console.log(`  removed ${fixed} bogus import(s)`); process.exit(0) }
if (bad) {
  console.log(`  ${bad} imported name(s) are not exported by their source — the module graph will not link.`)
  console.log('  Re-run with --fix to strip them.')
  process.exit(1)
}
console.log('  every imported name is exported by its source')
