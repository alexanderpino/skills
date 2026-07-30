// Export from legacy.js every helper the extracted plugins import.
//
// Written as a file rather than `node -e` because bash double-quoting turns "\\b" into "\b" — a
// literal BACKSPACE in the JS string, not a regex word boundary — so the match silently never
// fires and every symbol reports as missing. That has now cost three attempts across this session;
// patch scripts go in files.
const fs = require('fs');
const path = require('path');

const APP = path.resolve(__dirname, '..');
const LEGACY = path.join(APP, 'src', 'legacy.js');
const PLUGINS = path.join(APP, 'src', 'plugins');

let legacy = fs.readFileSync(LEGACY, 'utf8');

// collect every name imported from ../../legacy.js across all plugin modules
const need = new Set();
const walk = (dir) => {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { walk(p); continue; }
    if (!e.name.endsWith('.js')) continue;
    const s = fs.readFileSync(p, 'utf8');
    for (const m of s.matchAll(/import\s*\{([^}]+)\}\s*from\s*'[^']*legacy\.js'/g)) {
      m[1].split(',').map((x) => x.trim()).filter(Boolean).forEach((n) => need.add(n));
    }
  }
};
walk(PLUGINS);

const already = [];
const added = [];
const missing = [];

for (const n of [...need].sort()) {
  if (new RegExp(`^export\\s+(?:function|const|let|var)\\s+${n}\\b`, 'm').test(legacy)) {
    already.push(n);
    continue;
  }
  const re = new RegExp(`^(function|const|let|var)(\\s+${n}\\b)`, 'm');
  if (re.test(legacy)) {
    legacy = legacy.replace(re, (_m, kw, rest) => `export ${kw}${rest}`);
    added.push(n);
  } else {
    missing.push(n);
  }
}

fs.writeFileSync(LEGACY, legacy, 'utf8');

console.log(`  imported by plugins : ${[...need].sort().join(', ')}`);
console.log(`  already exported    : ${already.join(', ') || '(none)'}`);
console.log(`  newly exported      : ${added.join(', ') || '(none)'}`);
if (missing.length) {
  console.log(`  NOT FOUND in legacy : ${missing.join(', ')}`);
  process.exit(1);
}

// Verify each one really is exported now — the rewrite above is a regex and deserves a check that
// is not the same regex.
const bad = [...need].filter((n) => !new RegExp(`export\\s+(?:function|const|let|var)\\s+${n}\\b`).test(legacy));
if (bad.length) { console.log(`  VERIFY FAILED, still not exported: ${bad.join(', ')}`); process.exit(1); }
console.log(`  verified: all ${need.size} exported`);
