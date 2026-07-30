// Shared WebGL helpers. Framework-free, no DOM.
//
// gl is INJECTED, not imported. It is assigned inside initGL() in legacy.js, and importing it would
// make this module depend on the very file it is being carved out of. Injection keeps the
// dependency one-way.
//
// STORE THE CONTEXT, NEVER ITS METHODS. _verify_wireframe.js:93 replaces gl.drawElements and
// _verify_realtime.js:25 replaces gl.bindBuffer/bufferData, then classify the draws the app issues.
// Those patches only take if every call site dereferences gl.foo at CALL time. Caching
// `const draw = gl.drawElements` at module scope here would bypass the patch silently and the
// wireframe gate would go green measuring nothing.
let gl = null;
export const setGL = (ctx) => { gl = ctx; };

export function makeProg(vs,fs){function sh(t,s){const o=gl.createShader(t);gl.shaderSource(o,s);gl.compileShader(o);
  if(!gl.getShaderParameter(o,gl.COMPILE_STATUS))console.error(gl.getShaderInfoLog(o),s);return o;}
  const p=gl.createProgram();gl.attachShader(p,sh(gl.VERTEX_SHADER,vs));gl.attachShader(p,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);
  if(!gl.getProgramParameter(p,gl.LINK_STATUS))console.error(gl.getProgramInfoLog(p));return p;}

export function u(p,name){return gl.getUniformLocation(p,name);}
