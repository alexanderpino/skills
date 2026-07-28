// SHAPE SCAN — a mechanical completeness gate for the field-dimension conversion.
//
// `n` means field WIDTH and `nh` means field HEIGHT. Any surviving expression that uses the width
// where the row count is meant is a latent crop: it is inert while latticeRows(w) === w and becomes
// a dead or short bottom band the moment the lattice gets its true height. Grepping for that by eye
// does not work - a plan review of the first attempt found the naive pattern was permanently red on
// four lines that contain no standalone `n*n` at all (`margin*n/5`, `p.orogen*n*0.16`) and
// simultaneously blind to six sites the inventory itself named.
//
// Two corrections make it mechanical:
//   1. Both boundaries. `n*n` needs a LEFT guard as well as the `(?!h)` right guard, or it matches
//      inside `...*n*n...` products that have nothing to convert.
//   2. Exemption by MARKER, not by line number. Legitimately-square sites carry a `shape-ok`
//      comment naming why. Line numbers drift with every edit; a marker does not, and it documents
//      the reason at the site instead of in a manifest nobody reads.
//
// Usage: node _verify_shapescan.js   (exit 1 on any unexempted hit)
const fs = require('fs');
const path = require('path');
const FILE = process.env.SHAPESCAN_FILE || path.resolve(__dirname, 'index.html');
const src = fs.readFileSync(FILE, 'utf8');
const lines = src.split(/\r?\n/);

// Each rule: what it catches, and why that is a row-count defect.
const RULES = [
  { id: 'A-alloc', why: 'n*n where the field is n*nh (short allocation / truncated loop)',
    re: /(?<![A-Za-z0-9_.$])n\s*\*\s*n(?![A-Za-z0-9_$]|\s*\*\s*n)/g },
  { id: 'B-rowclamp', why: 'a row index clamped to the WIDTH (n-1) instead of the height (nh-1)',
    re: /(?:clamp\(\s*(?:y|sy|yy|py|ny)[^,]*,\s*0\s*,\s*n\s*-\s*1|Math\.min\(\s*n\s*-\s*1\s*,\s*(?:y|sy|yy)|Math\.min\(\s*(?:y|sy|yy)[^,]*,\s*n\s*-\s*1|Math\.min\(\s*n\s*,\s*(?:y|sy|yy))/g },
  { id: 'C-rowbound', why: 'a row loop or guard bounded by the WIDTH',
    re: /(?:\by\s*<\s*n\s*[-;)]|\byy\s*>=\s*n\b|\by\s*===\s*n\s*-\s*2|\by\s*<\s*nn\b|\byy\s*>=\s*nn\b|\by\s*<\s*RES\b)/g },
  { id: 'D-resres', why: 'RES*RES where the field is fieldLen()',
    re: /RES\s*\*\s*RES/g },
];

// A line is exempt only if it says so, in words, at the site.
const MARKER = /shape-ok/;

let hits = 0, exempt = 0;
const found = [];
lines.forEach((L, i) => {
  for (const r of RULES) {
    r.re.lastIndex = 0;
    if (r.re.test(L)) {
      if (MARKER.test(L)) { exempt++; continue; }
      hits++;
      found.push({ line: i + 1, rule: r.id, why: r.why, src: L.trim().slice(0, 118) });
    }
  }
});

console.log('== SHAPE SCAN ==  ' + path.basename(FILE));
for (const r of RULES) {
  const c = found.filter(f => f.rule === r.id).length;
  console.log('  ' + r.id.padEnd(12) + String(c).padStart(4) + '  ' + r.why);
}
console.log('  exempt (marked shape-ok): ' + exempt);
if (found.length) {
  console.log('\nunexempted hits:');
  for (const f of found) console.log('  ' + r_(f.line) + '  ' + f.rule.padEnd(12) + f.src);
}
function r_(n2) { return ('L' + n2).padEnd(7); }

if (found.length) {
  console.log('\nFAIL  shape-scan  ' + found.length + ' unexempted width-as-height site(s). '
    + 'Convert each to the row count, or mark it `shape-ok: <reason>` if it is legitimately square '
    + '(GPU textures are square by design; droplet counts are a cell-count proxy; the export PNG is '
    + 'a square interchange raster).');
  process.exit(1);
}
console.log('\nPASS  shape-scan  no unexempted site uses the field WIDTH where the row count is meant.');
process.exit(0);
