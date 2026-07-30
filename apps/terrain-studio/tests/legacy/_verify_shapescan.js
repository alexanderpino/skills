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
// ---------------------------------------------------------------------------------------------
// CORPUS: the scan follows the code, it does not follow the filename.
//
// This gate was a single `readFileSync(index.html)`. The app is about to become an ES module —
// the ~7200-line script body moves verbatim to src/legacy.js and index.html keeps only
// `<script type="module" src="./src/legacy.js"></script>`. A one-file scan does not notice. It
// reads the 931-line HTML shell, matches nothing, finds no markers, and prints
//
//     PASS  shape-scan  no unexempted site uses the field WIDTH where the row count is meant.
//
// with exit 0. Measured, not assumed: the pre-repair tool pointed at a synthetic split copy
// reported all six rules at 0 and `exemptions (0)` where the real answer is 11, and still exited 0.
// That is the same vacuous-gate shape this scan exists to prevent in the app: a Uint8Array sized
// n*n instead of n*rows silently dropped 13.4% of a hex field, because out-of-range TypedArray
// writes vanish without error. A gate that cannot fail on a moved build is worth exactly as much.
//
// So the target is a SET, resolved from globs, defaulting to the app's real source set:
// index.html today, index.html + src/**/*.js after the move — one default that is correct on both
// sides of the migration, so nobody has to remember to update it on the day.
//
// And the set is PROVEN non-vacuous before any verdict is printed:
//   * an empty resolved set is a FAILURE, not a pass;
//   * a set that resolves but contains none of the CANARY vocabulary these rules are written
//     against (JS syntax, the n/nh/RES field identifiers, typed-array field allocations) is a
//     FAILURE — that is precisely the "index.html is now a shell" case;
//   * the file count, the per-file line counts and the canary hit counts are PRINTED, so a human
//     reading a PASS can see the scan looked somewhere.
// A scan that finds nothing because it looked nowhere must never be able to say PASS.
//
// Usage: node _verify_shapescan.js            (exit 1 on any unexempted hit, or on an empty/dead corpus)
//        SHAPESCAN_FILE=<path|glob>[,<path|glob>...] node _verify_shapescan.js
//   Specs are comma- or semicolon-separated, absolute or relative to the app root. `*` matches
//   within one path segment, `**` spans directories. A bare directory expands to its .js/.html.
//   node_modules/, dist/, tests/ and build output are never swept up by a glob (an explicitly
//   named file is always honoured). A single path still works exactly as it did.
const fs = require('fs');
const path = require('path');

const APP_ROOT = path.resolve(__dirname, '../../');

// index.html today; index.html + src/**/*.js after the module split. Both entries are listed
// unconditionally: the answer must not depend on which side of the migration we are on.
const DEFAULT_TARGETS = ['index.html', 'src/**/*.js', 'src/**/*.mjs'];

// Never reached by a glob. `tests` is here because the oracles quote the very patterns the rules
// hunt for - scanning ourselves would report the gate's own source as a defect.
const EXCLUDE_DIRS = new Set([
  'node_modules', 'dist', 'tests', 'test-results', 'playwright-report',
  'coverage', '.git', '.vite', '.cache', 'satmaps',
]);

const posix = p => p.replace(/\\/g, '/');
// Inside the app tree, show the short relative path; outside it (a scratch copy, a worktree),
// show the absolute path. A `../../../../../Users/...` walk-up is unreadable and, worse, gives no
// hint that the scan left the app.
const rel = p => {
  const r = posix(path.relative(APP_ROOT, p));
  return (!r || r.startsWith('..') || path.isAbsolute(r)) ? posix(p) : r;
};
const isGlob = s => /[*?]/.test(s);

// `**/` spans zero-or-more directories; `*` and `?` stop at a separator. Windows paths are
// compared case-insensitively because the filesystem is.
function globToRegExp(pat) {
  let re = '';
  for (let i = 0; i < pat.length; i++) {
    const c = pat[i];
    if (c === '*') {
      if (pat[i + 1] === '*') {
        if (pat[i + 2] === '/') { re += '(?:[^/]+/)*'; i += 2; }
        else { re += '.*'; i += 1; }
      } else re += '[^/]*';
    } else if (c === '?') re += '[^/]';
    else re += c.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp('^' + re + '$', process.platform === 'win32' ? 'i' : '');
}

function walk(dir, out, depth) {
  if (depth > 12) return;                       // cheap guard against a symlink cycle
  let ents;
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return; }
  ents.sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));  // deterministic order
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (!EXCLUDE_DIRS.has(e.name)) walk(p, out, depth + 1); }
    else if (e.isFile()) out.push(p);
  }
}

// Resolve one spec to absolute file paths. Returns { spec, files, error }.
function resolveSpec(spec) {
  const abs = posix(path.isAbsolute(spec) ? path.resolve(spec) : path.resolve(APP_ROOT, spec));
  if (!isGlob(abs)) {
    let st = null;
    try { st = fs.statSync(abs); } catch (e) { /* missing */ }
    if (!st) return { spec, files: [], error: 'no such file or directory' };
    // A directory is a convenience form, not an error: scan the source it holds.
    if (st.isDirectory()) {
      const out = [];
      walk(abs, out, 0);
      return { spec, files: out.filter(f => /\.(?:js|mjs|html)$/i.test(f)).map(posix) };
    }
    return { spec, files: [abs] };              // named explicitly, so never excluded
  }
  const segs = abs.split('/');
  let cut = segs.length;
  for (let i = 0; i < segs.length; i++) if (isGlob(segs[i])) { cut = i; break; }
  const base = segs.slice(0, cut).join('/') || '/';
  const re = globToRegExp(abs);
  const out = [];
  walk(base, out, 0);
  return { spec, files: out.map(posix).filter(f => re.test(f)) };
}

const specs = (process.env.SHAPESCAN_FILE
  ? process.env.SHAPESCAN_FILE.split(/[;,]/).map(s => s.trim()).filter(Boolean)
  : DEFAULT_TARGETS);

const resolved = specs.map(resolveSpec);
const seen = new Set();
const FILES = [];
for (const r of resolved) for (const f of r.files) {
  const k = process.platform === 'win32' ? f.toLowerCase() : f;
  if (!seen.has(k)) { seen.add(k); FILES.push(f); }
}
const specErrors = resolved.filter(r => r.error);

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

// CANARIES — proof that the resolved corpus actually holds the code these rules are written
// against. Every one of these is measured at ZERO in the HTML shell that survives the module
// split and in the hundreds-to-thousands in the script body, so "index.html only, post-move"
// trips all three. They are deliberately about the gate's own subject matter: if the app stops
// using `nh` or stops allocating typed arrays, this gate's rules are stale and someone must
// look at it - a loud failure is the correct outcome, not a silent green.
const CANARIES = [
  { id: 'js-code', why: 'JavaScript at all (function / arrow / const|let binding)',
    re: /\bfunction\s*[A-Za-z_$(]|=>|\b(?:const|let)\s+[A-Za-z_$]/ },
  { id: 'field-vocab', why: 'the field-dimension identifiers these rules key on (nh / RES)',
    re: /\bnh\b|\bRES\b/ },
  { id: 'field-alloc', why: 'typed-array field allocations - the sites rule A guards',
    re: /new\s+(?:Float32|Float64|Uint8|Uint8Clamped|Uint16|Uint32|Int8|Int16|Int32)Array\s*\(/ },
];

// A line is exempt only if it says so IN WORDS at the site. A bare marker is not accepted: the
// whole point of exemption-by-marker is that the reason lives next to the code, and a rule that
// takes `shape-ok` alone would let an implementer silence every hard site invisibly and still
// print PASS - the shape every vacuous gate in this project has had.
const MARKER = /shape-ok:\s*\S/;
const BARE_MARKER = /shape-ok(?!\s*:\s*\S)/;

const found = [], exemptions = [], bare = [], floating = [];
const corpus = [];                       // { file, lines }
const canaryHits = new Map(CANARIES.map(c => [c.id, 0]));
let totalLines = 0;
const readErrors = [];

for (const f of FILES) {
  let src;
  try { src = fs.readFileSync(f, 'utf8'); } catch (e) { readErrors.push({ file: f, msg: e.message }); continue; }
  const lines = src.split(/\r?\n/);
  corpus.push({ file: rel(f), lines: lines.length });
  totalLines += lines.length;

  const firing = new Set(), markerLines = [];
  lines.forEach((L, i) => {
    for (const c of CANARIES) if (c.re.test(L)) canaryHits.set(c.id, canaryHits.get(c.id) + 1);
    if (/shape-ok/.test(L)) markerLines.push(i + 1);
    for (const r of RULES) {
      r.re.lastIndex = 0;
      if (r.re.test(L)) {
        if (MARKER.test(L)) {
          // Take the rest of the line. An earlier form stopped at `*` or `/`, which mangled almost
          // every real reason - reasons on n*n and (n-1)*(n-1) lines contain `*` by definition -
          // and the printed reason IS the audit for this gate.
          const m = L.match(/shape-ok:\s*(.*)$/);
          exemptions.push({ file: rel(f), line: i + 1, rule: r.id, reason: (m && m[1] || '').trim().slice(0, 90) });
          firing.add(i + 1);
          continue;
        }
        if (BARE_MARKER.test(L)) bare.push({ file: rel(f), line: i + 1, rule: r.id, src: L.trim().slice(0, 100) });
        found.push({ file: rel(f), line: i + 1, rule: r.id, why: r.why, src: L.trim().slice(0, 118) });
      }
    }
  });

  // A marker that sits on a line no rule fires on is FREE-FLOATING: it documents nothing the
  // scanner checked, and it silently pre-approves that line if a future rule ever reaches it.
  // A cross-model review counted 15 markers against 11 real exemptions. Report the difference.
  for (const l of markerLines) {
    if (!firing.has(l)) floating.push({ file: rel(f), line: l, src: (lines[l - 1] || '').trim().slice(0, 100) });
  }
}

// ---------------------------------------------------------------------------------------------
// Report. The corpus block comes FIRST and is unconditional: it is the evidence that the verdict
// below is about something.
// ---------------------------------------------------------------------------------------------
console.log('== SHAPE SCAN ==  ' + FILES.length + ' file(s), ' + totalLines + ' line(s)');
console.log('  targets: ' + specs.join('  '));
const fw = Math.max(4, ...corpus.map(c => c.file.length));
for (const c of corpus) console.log('    ' + c.file.padEnd(fw) + String(c.lines).padStart(8) + ' lines');
if (!corpus.length) console.log('    (no files resolved)');
for (const r of specErrors) console.log('    !! ' + r.spec + '  -> ' + r.error);
for (const r of readErrors) console.log('    !! ' + rel(r.file) + '  -> ' + r.msg);

console.log('\ncorpus proof (the scan is looking at real code, not an empty shell):');
for (const c of CANARIES) {
  console.log('  ' + c.id.padEnd(12) + String(canaryHits.get(c.id)).padStart(6) + '  ' + c.why);
}

console.log('');
for (const r of RULES) {
  const c = found.filter(f => f.rule === r.id).length;
  console.log('  ' + r.id.padEnd(12) + String(c).padStart(4) + '  ' + r.why);
}

const labels = [...exemptions, ...bare, ...found, ...floating].map(x => x.file + ':' + x.line);
const lw = Math.max(6, ...labels.map(l => l.length));
const at = x => (x.file + ':' + x.line).padEnd(lw) + '  ';

// Exemptions are ENUMERATED with their reasons, never summarised as a count. A number nobody reads
// is exactly how 27 hard sites get silenced behind a green result.
console.log('\nexemptions (' + exemptions.length + '):');
for (const e of exemptions) console.log('  ' + at(e) + e.rule.padEnd(12) + e.reason);
if (!exemptions.length) console.log('  (none)');

if (floating.length) {
  console.log('\nFREE-FLOATING shape-ok markers (no rule fires on these lines):');
  for (const f of floating) console.log('  ' + at(f) + f.src);
}

if (bare.length) {
  console.log('\nBARE MARKERS - `shape-ok` with no reason, not accepted:');
  for (const b of bare) console.log('  ' + at(b) + b.rule.padEnd(12) + b.src);
}

if (found.length) {
  console.log('\nunexempted hits:');
  for (const f of found) console.log('  ' + at(f) + f.rule.padEnd(12) + f.src);
}

// ---------------------------------------------------------------------------------------------
// Verdict. The corpus checks are evaluated BEFORE the findings, because "no findings" is only
// meaningful once the corpus is known to be real.
// ---------------------------------------------------------------------------------------------
let bad = 0;
if (specErrors.length) {
  console.log('\nFAIL  shapescan-targets  ' + specErrors.length + ' target spec(s) resolved to nothing that exists: '
    + specErrors.map(r => r.spec).join(', ') + '. A scan cannot report on a file it never opened.');
  bad++;
}
if (readErrors.length) {
  console.log('\nFAIL  shapescan-unreadable  ' + readErrors.length + ' resolved file(s) could not be read.');
  bad++;
}
if (!FILES.length) {
  console.log('\nFAIL  shapescan-empty-corpus  the target set resolved to ZERO files (targets: '
    + specs.join(', ') + '). This is a failure, never a pass: a scan that finds nothing because it '
    + 'looked nowhere is the exact defect this gate exists to prevent. Point SHAPESCAN_FILE at the '
    + 'app source, or fix the default if the layout moved.');
  bad++;
} else {
  const dead = CANARIES.filter(c => canaryHits.get(c.id) === 0);
  if (dead.length) {
    console.log('\nFAIL  shapescan-dead-corpus  the resolved file set contains NO scannable code: '
      + dead.map(c => c.id).join(', ') + ' matched zero lines across ' + FILES.length + ' file(s) / '
      + totalLines + ' line(s). The usual cause is that the script body moved out of index.html into '
      + 'src/ and the scan is reading the leftover HTML shell — six rules at 0 out of an empty shell '
      + 'is not a pass. Widen the target set (default: ' + DEFAULT_TARGETS.join(', ') + ').');
    bad++;
  }
}
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
  console.log('\nPASS  shape-scan  no unexempted site uses the field WIDTH where the row count is meant.'
    + '  (' + FILES.length + ' file(s), ' + totalLines + ' line(s) scanned)');
}
process.exit(bad ? 1 : 0);
