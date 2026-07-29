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
const FILE = process.env.SHAPESCAN_FILE || path.resolve(__dirname, '../../index.html');
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
  // Rules E and F exist because a review found the four rules above were blind to the entire
  // wireframe family and to streamPowerErode's bottom-edge marking - sites that consequently had
  // NO gate at all, on either criterion. (n-1)*(n-1) is a quad count over a square grid, and
  // (n-1)*n is a "last row" computed from the width.
  { id: 'E-quadcount', why: '(n-1)*(n-1) quad/edge count over a SQUARE grid; the hex form is (n-1)*(nh-1)',
    re: /\(\s*n\s*-\s*1\s*\)\s*\*\s*\(\s*n\s*-\s*1\s*\)/g },
  { id: 'F-lastrow', why: '(n-1)*n computes a LAST ROW from the width; the last row is (nh-1)*n',
    re: /\(\s*n\s*-\s*1\s*\)\s*\*\s*n\b/g },
];

// A line is exempt only if it says so IN WORDS at the site. A bare marker is not accepted: the
// whole point of exemption-by-marker is that the reason lives next to the code, and a rule that
// takes `shape-ok` alone would let an implementer silence every hard site invisibly and still
// print PASS - the shape every vacuous gate in this project has had.
const MARKER = /shape-ok:\s*\S/;
const BARE_MARKER = /shape-ok(?!\s*:\s*\S)/;

const found = [], exemptions = [], bare = [];
lines.forEach((L, i) => {
  for (const r of RULES) {
    r.re.lastIndex = 0;
    if (r.re.test(L)) {
      if (MARKER.test(L)) {
        // Take the rest of the line. An earlier form stopped at `*` or `/`, which mangled almost
        // every real reason - reasons on n*n and (n-1)*(n-1) lines contain `*` by definition - and
        // the printed reason IS the audit for this gate.
        const m = L.match(/shape-ok:\s*(.*)$/);
        exemptions.push({ line: i + 1, rule: r.id, reason: (m && m[1] || '').trim().slice(0, 90) });
        continue;
      }
      if (BARE_MARKER.test(L)) bare.push({ line: i + 1, rule: r.id, src: L.trim().slice(0, 100) });
      found.push({ line: i + 1, rule: r.id, why: r.why, src: L.trim().slice(0, 118) });
    }
  }
});

const pad = n2 => ('L' + n2).padEnd(7);
console.log('== SHAPE SCAN ==  ' + path.basename(FILE));
for (const r of RULES) {
  const c = found.filter(f => f.rule === r.id).length;
  console.log('  ' + r.id.padEnd(12) + String(c).padStart(4) + '  ' + r.why);
}

// Exemptions are ENUMERATED with their reasons, never summarised as a count. A number nobody reads
// is exactly how 27 hard sites get silenced behind a green result.
console.log('\nexemptions (' + exemptions.length + '):');
for (const e of exemptions) console.log('  ' + pad(e.line) + '  ' + e.rule.padEnd(12) + e.reason);
if (!exemptions.length) console.log('  (none)');

// A marker that sits on a line no rule fires on is FREE-FLOATING: it documents nothing the
// scanner checked, and it silently pre-approves that line if a future rule ever reaches it.
// A cross-model review counted 15 markers against 11 real exemptions. Report the difference.
const markerLines = [];
lines.forEach((L2, i) => { if (/shape-ok/.test(L2)) markerLines.push(i + 1); });
const firing = new Set(exemptions.map(e => e.line));
const floating = markerLines.filter(l => !firing.has(l));
if (floating.length) {
  console.log('\nFREE-FLOATING shape-ok markers (no rule fires on these lines):');
  for (const l of floating) console.log('  ' + pad(l) + '  ' + (lines[l - 1] || '').trim().slice(0, 100));
}

if (bare.length) {
  console.log('\nBARE MARKERS - `shape-ok` with no reason, not accepted:');
  for (const b of bare) console.log('  ' + pad(b.line) + '  ' + b.rule.padEnd(12) + b.src);
}

if (found.length) {
  console.log('\nunexempted hits:');
  for (const f of found) console.log('  ' + pad(f.line) + '  ' + f.rule.padEnd(12) + f.src);
}

let bad = 0;
if (bare.length) {
  console.log('\nFAIL  exemption-reasons  ' + bare.length + ' site(s) carry a bare `shape-ok`. '
    + 'Write `shape-ok: <why this is legitimately square>` - the reason is the audit.');
  bad++;
}
if (floating.length) {
  console.log('\nFAIL  free-floating-markers  ' + floating.length
    + ' shape-ok marker(s) sit on lines no rule fires on. Remove them, or move them to the line the '
    + 'scanner actually flags - an unaudited marker is a pre-approval nobody reviewed.');
  bad++;
}
if (found.length) {
  console.log('\nFAIL  shape-scan  ' + found.length + ' unexempted width-as-height site(s). '
    + 'Convert each to the row count, or mark it `shape-ok: <reason>` if it is legitimately square '
    + '(GPU textures are square by design this phase; droplet counts are a cell-count proxy; the '
    + 'export PNG is a square interchange raster; one prose comment mentions n*n and needs a marker).');
  bad++;
} else if (!bad) {
  console.log('\nPASS  shape-scan  no unexempted site uses the field WIDTH where the row count is meant.');
}
process.exit(bad ? 1 : 0);
