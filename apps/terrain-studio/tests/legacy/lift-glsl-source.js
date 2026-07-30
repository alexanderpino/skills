// Lift GLSL function bodies out of the app's OWN source, wherever that source currently lives.
//
// WHY THIS EXISTS AS A SHARED MODULE. Two oracles compile a probe shader out of functions
// brace-matched from the shipped app source, so the shader under test cannot drift from what
// actually ships: _verify_glsl_probe.js and _verify_hex_deferred.js. Both hard-coded
// fs.readFileSync('../../index.html'), and both therefore stop finding anything the moment
// step A1 moves the inline classic <script> body into src/legacy.js. _verify_glsl_probe.js is
// wired to this module; _verify_hex_deferred.js is owned elsewhere and still has the old copy.
//
// The failure mode this closes is not "the tool errors", it is "the tool keeps exiting 0".
// Measured on a synthetic A1-split copy, the old code lifted null for both functions,
// interpolated the STRING "null" into the fragment shader, got
//     fsOk:false  fsLog:"ERROR: 0:5: 'null' : syntax error"
// printed `"samples": []` and exited 0. Nothing was compared and the run looked clean. So this
// module never returns a silent null: callers get an explicit missing/ambiguous report, and
// liftOrDie() terminates the process with a non-zero exit and the list of files it searched.
//
// RESOLUTION ORDER (deterministic, and identical before and after A1):
//   1. <root>/index.html                     - the whole file, inline <script> and all
//   2. <root>/src/**/*.js  sorted by path    - where the script body lives after A1
// Both are always searched, so today's single-file app and tomorrow's module split give the
// same answer without a flag day. dist/, node_modules/ and the rest of the app are NOT searched:
// a built bundle is a copy, and lifting from a copy is how you end up verifying stale GLSL.
//
// PATH OVERRIDE, following the suite's convention (BRIDGE_APP in _verify_bridge.js,
// SHAPESCAN_FILE in _verify_shapescan.js, STUDIO_URL in the browser oracles):
//
//   GLSL_SRC=<dir>    treat that directory as the app root and run the two steps above in it
//   GLSL_SRC=<file>   search exactly that one file
//
// The directory form is what makes this testable: point it at a synthetic module-split copy and
// assert the lifted text is byte-identical to what the unsplit app yields.
'use strict';

const fs = require('fs');
const path = require('path');

const ENV_VAR = 'GLSL_SRC';
// tests/legacy/ -> apps/terrain-studio/
const APP_ROOT = path.resolve(__dirname, '../..');

// ---------------------------------------------------------------------------
// Source resolution
// ---------------------------------------------------------------------------
function collectJs(dir, root, out) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch (_) { return; }
  entries.sort((a, b) => a.name.localeCompare(b.name));
  for (const e of entries) {
    const abs = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name.startsWith('.')) continue;
      collectJs(abs, root, out);
    } else if (e.isFile() && /\.(?:js|mjs)$/.test(e.name)) {
      out.push({ abs, rel: path.relative(root, abs).replace(/\\/g, '/') });
    }
  }
}

// -> { envVar, mode, root, override, files:[{abs, rel, text}], searched:[rel] }
// Throws only for an override that does not exist at all; an app root with no readable source
// is reported as an empty file list so the caller can name it in ITS failure message.
function resolveSources(opts) {
  const o = opts || {};
  const override = o.src || process.env[ENV_VAR] || null;

  let root = o.root ? path.resolve(o.root) : APP_ROOT;
  let mode = 'app';

  if (override) {
    const p = path.resolve(override);
    if (!fs.existsSync(p)) {
      const e = new Error(`${ENV_VAR} points at a path that does not exist: ${p}`);
      e.code = 'GLSL_SRC_MISSING';
      throw e;
    }
    if (fs.statSync(p).isDirectory()) { root = p; mode = 'app'; }
    else { mode = 'file'; root = path.dirname(p); }
  }

  const picked = [];
  if (mode === 'file') {
    const p = path.resolve(override);
    picked.push({ abs: p, rel: path.basename(p) });
  } else {
    const html = path.join(root, 'index.html');
    if (fs.existsSync(html)) picked.push({ abs: html, rel: 'index.html' });
    const srcDir = path.join(root, 'src');
    if (fs.existsSync(srcDir) && fs.statSync(srcDir).isDirectory()) collectJs(srcDir, root, picked);
  }

  const files = [];
  for (const f of picked) {
    let text;
    try { text = fs.readFileSync(f.abs, 'utf8'); } catch (_) { continue; }
    files.push({ abs: f.abs, rel: f.rel, text });
  }

  return {
    envVar: ENV_VAR, mode, root, override,
    files,
    searched: files.map((f) => f.rel),
  };
}

// ---------------------------------------------------------------------------
// Brace matching
// ---------------------------------------------------------------------------
// Byte-for-byte the algorithm both oracles already used, so a repaired tool cannot quietly
// change what it compiles: first occurrence of the signature, first '{' at or after it, slice
// through the '}' that closes it.
function braceMatch(text, sig) {
  const i = text.indexOf(sig);
  if (i < 0) return null;
  let d = 0;
  const j = text.indexOf('{', i);
  if (j < 0) return null;
  for (let k = j; k < text.length; k++) {
    if (text[k] === '{') d++;
    else if (text[k] === '}') { d--; if (!d) return { code: text.slice(i, k + 1), index: i }; }
  }
  return null;
}

const lineOf = (text, i) => text.slice(0, i).split('\n').length;

// ---------------------------------------------------------------------------
// lift
// ---------------------------------------------------------------------------
// -> { ok, sources, found:{sig:{code,file,line}}, code:{sig:code}, missing:[sig],
//      ambiguous:[{sig, files:[rel]}], unclosed:[{sig, file}] }
//
// ambiguous is a REAL failure, not pedantry: if two shipped files both define the function, the
// probe cannot know which one the page actually loaded, and picking one is how a green run comes
// to certify code that is not running.
function lift(signatures, opts) {
  const sources = resolveSources(opts);
  const found = Object.create(null);
  const code = Object.create(null);
  const missing = [];
  const ambiguous = [];
  const unclosed = [];

  for (const sig of signatures) {
    const hits = [];
    for (const f of sources.files) {
      if (f.text.indexOf(sig) < 0) continue;
      const m = braceMatch(f.text, sig);
      if (!m) { unclosed.push({ sig, file: f.rel }); continue; }
      hits.push({ file: f.rel, code: m.code, line: lineOf(f.text, m.index) });
    }
    if (!hits.length) { missing.push(sig); continue; }
    if (hits.length > 1) { ambiguous.push({ sig, files: hits.map((h) => h.file) }); continue; }
    found[sig] = hits[0];
    code[sig] = hits[0].code;
  }

  const ok = !missing.length && !ambiguous.length && !unclosed.length;
  return { ok, sources, found, code, missing, ambiguous, unclosed };
}

// Human-readable "which one, and where did you look" report. Named signatures, named files.
function failureReport(res) {
  const s = res.sources;
  const L = [];
  for (const sig of res.missing) L.push(`  MISSING   ${sig}...)  - not found in any searched file`);
  for (const a of res.ambiguous) {
    L.push(`  AMBIGUOUS ${a.sig}...)  - defined in ${a.files.length} files: ${a.files.join(', ')}`);
  }
  for (const u of res.unclosed) L.push(`  UNCLOSED  ${u.sig}...)  - found in ${u.file} but its braces never close`);
  L.push('');
  L.push(`  source mode : ${s.mode}${s.override ? ` (${s.envVar}=${s.override})` : ''}`);
  L.push(`  app root    : ${s.root}`);
  L.push(`  searched    : ${s.searched.length ? s.searched.join(', ') : '(nothing readable)'}`);
  L.push('');
  L.push('  After the ES-module split these live in src/legacy.js, not index.html. Both are');
  L.push(`  searched by default; override with ${s.envVar}=<app-dir> or ${s.envVar}=<file>.`);
  return L.join('\n');
}

// The loud path. Returns { sig: code } or terminates the run. No caller can accidentally
// interpolate a null into a shader source through this.
function liftOrDie(signatures, opts) {
  let res;
  try {
    res = lift(signatures, opts);
  } catch (e) {
    console.error(`SETUP FAILURE: ${e.message}`);
    process.exit(2);
  }
  if (!res.ok) {
    const label = (opts && opts.label) || 'the probe shader';
    console.error(`SETUP FAILURE: could not lift ${label} from the app source.`);
    console.error(failureReport(res));
    process.exit(2);
  }
  return res;
}

module.exports = { ENV_VAR, APP_ROOT, resolveSources, braceMatch, lift, failureReport, liftOrDie };
