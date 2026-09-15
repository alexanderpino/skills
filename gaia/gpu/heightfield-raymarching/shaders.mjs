// GLSL ES 3.00 source for the shaders used by measure.mjs.
//
// The march shader below is a LITERAL transcription of heightfield-raymarching.md's :61-82
// fence, kept line-for-line comparable to the fence and to `_march` in
// gaia/rigs/approx/heightfield-raymarching.py -- so a divergence between this shader's
// output and the Python rig's is attributable to the SHADER LANGUAGE, not to two different
// algorithms. Anything the page leaves unspecified (exitDistance's DDA form, the refine's
// exact bisection) is implemented exactly as the Python rig implements it, for the same
// reason: two arbitrary choices would make disagreement uninformative.

export const VS_FULLSCREEN = `#version 300 es
in vec2 aPos;
void main() { gl_Position = vec4(aPos, 0.0, 1.0); }
`;

// Each output pixel is ONE RAY. Column x of the output = ray index x.
// Height field and its mip pyramid are supplied as textures (see measure.mjs for how the
// pyramid is built -- 3x3-dilated base, then max-reduced, matching _pyramid(h, "level0")).
export const FS_MARCH = `#version 300 es
precision highp float;
precision highp int;
precision highp sampler2D;

uniform sampler2D uRays;        // width = NUM_RAYS, 2 texels/ray: [ox,oy,oz,t0] [dx,dy,dz,t1]
uniform sampler2D uPyramid[8];  // level 0..NLEVELS-1, each level i is (NG>>i) square, R32F
uniform int   uNLevels;
uniform float uS0;
uniform int   uNG;
uniform int   uBisections;      // 5, 6 or 8 -- the page's own stated range at :70/:286
uniform int   uStepCap;         // :80's belt -- a literal, not the termination argument

out vec4 oResult;               // .x = hit t (or -1 for miss), .y = steps taken, .z = level at exit

// ---- registration, per :145-150, pinned as prose in the page and transcribed here -------
// "A level-L texel (i,j) owns the half-open square [i*s_L, (i+1)*s_L)... texelAt is
// floor(pos.xz / s_L), never a rounded texel-centre lookup."
float texelAt(sampler2D lvlTex, vec2 posXZ, float sL, int ng) {
  // _node_max: 'pyr[level][floor(z/s) % n][floor(x/s) % n]' -- WRAPS, does not clamp. The
  // field is periodic (the dilate3 apron itself wraps -- ":146-147... Periodic, so floor
  // wraps exactly"), and clamping here was this port's own bug: any ray whose projected
  // (x,z) drifts outside [0, ng*sL) -- which oblique "primary" rays do routinely -- read a
  // clamped edge texel instead of the correct wrapped one, and disagreed with the Python
  // rig by tens of metres. GLSL's mod() on a negative float already returns a non-negative
  // result matching Python's %, so no extra correction is needed the way JS needed one.
  ivec2 cell = ivec2(floor(posXZ / sL));
  cell = ivec2(mod(float(cell.x), float(ng)), mod(float(cell.y), float(ng)));
  return texelFetch(lvlTex, cell, 0).r;               // texelFetch: explicit LOD, never a filtered Sample
}

float fetchLevel(int level, vec2 posXZ, float sL, int ng) {
  // GLSL forbids indexing a sampler array with a non-constant expression pre-ES3.1 in some
  // profiles; ES 3.00 permits dynamic indexing of sampler arrays used only for texelFetch/texture
  // in a fragment shader on most implementations INCLUDING SwiftShader/ANGLE, verified in caps.mjs.
  if (level == 0) return texelAt(uPyramid[0], posXZ, sL, ng);
  if (level == 1) return texelAt(uPyramid[1], posXZ, sL, ng);
  if (level == 2) return texelAt(uPyramid[2], posXZ, sL, ng);
  if (level == 3) return texelAt(uPyramid[3], posXZ, sL, ng);
  if (level == 4) return texelAt(uPyramid[4], posXZ, sL, ng);
  if (level == 5) return texelAt(uPyramid[5], posXZ, sL, ng);
  if (level == 6) return texelAt(uPyramid[6], posXZ, sL, ng);
  return texelAt(uPyramid[7], posXZ, sL, ng);
}

// exitDistance: DDA to the node boundary. +inf (here: a very large sentinel) for an axis the
// ray does not move along -- ported unchanged from _exit_distance() in the Python rig.
float exitDistance(vec3 o, vec3 d, float t, int level) {
  float s = uS0 * float(1 << level);
  float out_ = 1.0e30;
  if (d.x != 0.0) {
    float c = floor((o.x + d.x * t) / s);
    float bound = (c + (d.x > 0.0 ? 1.0 : 0.0)) * s;
    out_ = min(out_, (bound - o.x) / d.x);
  }
  if (d.z != 0.0) {
    float c = floor((o.z + d.z * t) / s);
    float bound = (c + (d.z > 0.0 ? 1.0 : 0.0)) * s;
    out_ = min(out_, (bound - o.z) / d.z);
  }
  return out_;
}

float rayHeightAt(vec3 o, vec3 d, float t) { return o.y + d.y * t; }

// Bilinear reconstruction of the BASE field, for the refine step -- matches _surface(),
// which WRAPS ('i % _NG', '(i+1) % _NG'), not clamps. Same bug class as texelAt above.
uniform sampler2D uBase;  // level-0 samples, NOT dilated, R32F, NG x NG
ivec2 wrapIdx(vec2 c, int ng) {
  return ivec2(mod(float(int(floor(c.x))), float(ng)), mod(float(int(floor(c.y))), float(ng)));
}
float surface(vec2 posXZ) {
  vec2 c = posXZ / uS0 - 0.5;
  vec2 c0 = floor(c);
  vec2 f = c - c0;
  ivec2 i00 = wrapIdx(c0, uNG);
  ivec2 i10 = wrapIdx(c0 + vec2(1.0, 0.0), uNG);
  ivec2 i01 = wrapIdx(c0 + vec2(0.0, 1.0), uNG);
  ivec2 i11 = wrapIdx(c0 + vec2(1.0, 1.0), uNG);
  float h00 = texelFetch(uBase, i00, 0).r, h10 = texelFetch(uBase, i10, 0).r;
  float h01 = texelFetch(uBase, i01, 0).r, h11 = texelFetch(uBase, i11, 0).r;
  return mix(mix(h00, h10, f.x), mix(h01, h11, f.x), f.y);
}

// Ported from _refine(), not from the fence's one-line "binary or secant refine": the fence
// returns refine(t, tExitNode) UNCONDITIONALLY, which the page's own :286 failure-table row
// names as a defect ("a refine that finds no crossing must fall through and keep marching").
// _refine has TWO deviations from that literal line, both forced, both reproduced here:
//   1. 'binary refine' presupposes a BRACKET, and a level-0 span need not have one -- inside
//      one texel a bilinear surface can dip below the ray and come back. A fixed SCAN=8-step
//      linear search finds the bracket before bisecting.
//   2. if no bracket is found, this returns false via 'hit' (Python returns None), which the
//      caller must treat as "no hit here", NOT as a hit at the midpoint -- see main() below.
const int SCAN = 8;
float sampleF(vec3 o, vec3 d, float t) { return rayHeightAt(o, d, t) - surface(o.xz + d.xz * t); }

bool refine(vec3 o, vec3 d, float t0, float t1, out float hit) {
  float flo = sampleF(o, d, t0);
  if (flo <= 0.0) { hit = t0; return true; }
  float fhi = sampleF(o, d, t1);
  float lo = t0, hi = t1;
  if (!(fhi <= 0.0)) {
    float prevT = t0, prevF = flo;
    bool found = false;
    for (int si = 1; si <= SCAN; si++) {
      float tt = t0 + (t1 - t0) * float(si) / float(SCAN);
      float ft = sampleF(o, d, tt);
      if (prevF > 0.0 && ft <= 0.0) { lo = prevT; hi = tt; found = true; break; }
      prevT = tt; prevF = ft;
    }
    if (!found) { hit = -1.0; return false; }
  }
  // Invariant established above (and by _refine's own reasoning): f(lo) > 0, f(hi) <= 0.
  // Each step keeps that invariant rather than testing against a captured f0.
  for (int i = 0; i < 8; i++) {
    if (i >= uBisections) break;
    float m = 0.5 * (lo + hi);
    if (sampleF(o, d, m) > 0.0) { lo = m; } else { hi = m; }
  }
  hit = 0.5 * (lo + hi);
  return true;
}

// Ported from _march(), not from the fence's literal text: the fence's 'if (level == 0)
// return refine(...)' returns UNCONDITIONALLY, which the page itself calls a defect (:70,
// :286). _march's actual control flow -- which is what the closed-form reference this shader
// is checked against was ALSO checked against -- runs the candidate branch, and THEN checks
// '(not candidate) or (level == level_before)' to decide whether to ALSO advance in the same
// iteration. That composite condition is what lets a failed level-0 refine fall through to
// the pop-up step instead of returning a hit the interval test only said was POSSIBLE.
void main() {
  int rayIdx = int(gl_FragCoord.x);
  vec4 r0 = texelFetch(uRays, ivec2(0, rayIdx), 0);
  vec4 r1 = texelFetch(uRays, ivec2(1, rayIdx), 0);
  vec3 o = r0.xyz, d = r1.xyz;
  float tEnter = r0.w, tExit = r1.w;

  int level = uNLevels - 1;              // level = coarsestMip
  float t = tEnter;                      // t = tEnter
  int steps = 0;                         // steps = 0
  float hitT = -1.0;
  int exitLevel = level;

  for (int iter = 0; iter < 100000; iter++) {
    if (!(t < tExit)) break;             // while (t < tExit)
    float sL = uS0 * float(1 << level);
    float node = fetchLevel(level, o.xz + d.xz * t, sL, uNG);   // node_max
    float tExitNode = min(exitDistance(o, d, t, level), tExit); // CLAMPED (_F_CLAMP is true)

    float h0 = rayHeightAt(o, d, t), h1 = rayHeightAt(o, d, tExitNode);
    bool candidate = min(h0, h1) < node;
    float tBefore = t;
    int levelBefore = level;


    if (candidate) {
      if (level == 0) {
        float hit;
        bool found = refine(o, d, t, tExitNode, hit);
        if (found) { hitT = hit; exitLevel = 0; steps = steps + 1; break; }
        // no bracket: level stays 0 (== levelBefore), falls through to the shared advance
        // check below exactly as _march's 'if (not candidate) or level == level_before:' does
      } else {
        if (d.y < 0.0) {                                    // DESCENDING-ray guard
          float tCross = (node - o.y) / d.y;                // d.y < 0 here, never zero
          t = max(t, tCross);
        }
        level = level - 1;                                  // descend
      }
    }
    if ((!candidate) || (level == levelBefore)) {
      t = max(t, tExitNode) * (1.0 + 2.38418579e-7);         // RELATIVE step, never + eps
      level = min(level + 1, uNLevels - 1);                  // pop up, CLAMPED
    }
    steps = steps + 1;
    exitLevel = level;
    if (steps > uStepCap) { hitT = -2.0; break; }             // the belt, not the argument
  }

  oResult = vec4(hitT, float(steps), float(exitLevel), 0.0);
}
`;
