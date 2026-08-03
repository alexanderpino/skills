// Bounded expression grammar for the Math node — ADR-004, story S8.4.
//
// Pure and DOM-free. Parses to an AST and evaluates that AST. It never builds a Function, never
// calls eval, and never touches a global: the only names an expression can reach are the ones
// handed to it. A terrain graph is a document users share, and a document that can execute
// arbitrary JavaScript when opened is a different kind of artefact entirely.
//
// BOUNDED means bounded in three separate ways, because each catches a different abuse:
//   * the ALLOWLIST decides which functions exist at all
//   * MAX_NODES bounds the parsed program, so a pathological expression cannot be pasted in
//   * MAX_DEPTH bounds nesting, so parsing cannot blow the JS stack before limits apply
//
// Every result is finiteness-checked. `1/0` is Infinity and `0/0` is NaN in IEEE-754, and both
// spread silently through a terrain field until something far downstream produces a black tile —
// so they are refused at the source, named.

export const EXPR_MAX_NODES = 256
export const EXPR_MAX_DEPTH = 32

// Arity is declared so a wrong-arity call is a parse error rather than a silent undefined.
export const EXPR_FUNCTIONS = Object.freeze(Object.assign(Object.create(null), {
  abs: { arity: 1, fn: Math.abs }, min: { arity: 2, fn: Math.min }, max: { arity: 2, fn: Math.max },
  floor: { arity: 1, fn: Math.floor }, ceil: { arity: 1, fn: Math.ceil }, round: { arity: 1, fn: Math.round },
  sqrt: { arity: 1, fn: Math.sqrt }, exp: { arity: 1, fn: Math.exp }, log: { arity: 1, fn: Math.log },
  sin: { arity: 1, fn: Math.sin }, cos: { arity: 1, fn: Math.cos }, tan: { arity: 1, fn: Math.tan },
  atan2: { arity: 2, fn: Math.atan2 }, pow: { arity: 2, fn: Math.pow }, sign: { arity: 1, fn: Math.sign },
  clamp: { arity: 3, fn: (v, lo, hi) => Math.min(Math.max(v, lo), hi) },
  lerp: { arity: 3, fn: (a, b, t) => a + (b - a) * t },
  step: { arity: 2, fn: (edge, v) => (v < edge ? 0 : 1) },
}))

// NULL-PROTOTYPE, and this is not decoration. With a normal object literal, `'constructor' in
// EXPR_CONSTANTS` is TRUE — `in` walks the prototype chain — so the expression `constructor` parsed
// as a numeric literal whose value was the Object CONSTRUCTOR rather than being refused as an
// unknown name. Same for toString, valueOf, __proto__ and hasOwnProperty. A node whose entire
// selling point is that expressions cannot reach anything must not hand them Object on request.
// The oracle caught this: 7 of 8 escape attempts refused, and the one that got through was
// `constructor`.
export const EXPR_CONSTANTS = Object.freeze(Object.assign(Object.create(null), { pi: Math.PI, e: Math.E, tau: Math.PI * 2 }))

export const EXPR_ERROR_CODES = Object.freeze([
  'EXPR_SYNTAX', 'EXPR_UNKNOWN_NAME', 'EXPR_UNKNOWN_FUNCTION', 'EXPR_ARITY',
  'EXPR_TOO_LARGE', 'EXPR_TOO_DEEP', 'EXPR_NOT_FINITE', 'EXPR_DIVIDE_BY_ZERO',
])

export class ExprError extends Error {
  constructor(code, message, detail) { super(message); this.name = 'ExprError'; this.code = code; this.detail = detail }
}
const fail = (code, message, detail) => { throw new ExprError(code, message, detail) }

const TOKEN = /\s*([A-Za-z_][A-Za-z0-9_]*|\d+\.?\d*(?:[eE][+-]?\d+)?|\*\*|[-+*/%(),^]|<=|>=|<|>|==|!=|\?|:)/y

function tokenize(src) {
  const tokens = []
  let i = 0
  while (i < src.length) {
    TOKEN.lastIndex = i
    const m = TOKEN.exec(src)
    if (!m) {
      if (!src.slice(i).trim()) break
      fail('EXPR_SYNTAX', `unexpected character at ${i}: ${JSON.stringify(src[i])}`, { at: i })
    }
    tokens.push(m[1])
    i = TOKEN.lastIndex
  }
  return tokens
}

/**
 * Parse to an AST. Precedence climbing; `^` and `**` are power and right-associative.
 * `names` is the set of legal identifiers — inputs and declared variables. Anything else is
 * EXPR_UNKNOWN_NAME rather than undefined-at-runtime, so a typo is caught when the user types it.
 */
export function parseExpr(src, { names = [] } = {}) {
  const tokens = tokenize(String(src == null ? '' : src))
  if (!tokens.length) fail('EXPR_SYNTAX', 'empty expression')
  const legal = new Set(names)
  let pos = 0, count = 0
  const peek = () => tokens[pos]
  const take = () => tokens[pos++]
  const node = n => { if (++count > EXPR_MAX_NODES) fail('EXPR_TOO_LARGE', `expression exceeds ${EXPR_MAX_NODES} nodes`, { limit: EXPR_MAX_NODES }); return n }

  function primary(depth) {
    if (depth > EXPR_MAX_DEPTH) fail('EXPR_TOO_DEEP', `expression nests deeper than ${EXPR_MAX_DEPTH}`, { limit: EXPR_MAX_DEPTH })
    const t = take()
    if (t === undefined) fail('EXPR_SYNTAX', 'unexpected end of expression')
    if (t === '(') { const e = ternary(depth + 1); if (take() !== ')') fail('EXPR_SYNTAX', 'missing )'); return e }
    if (t === '-') return node({ k: 'neg', a: primary(depth + 1) })
    if (t === '+') return primary(depth + 1)
    if (/^\d/.test(t)) return node({ k: 'num', v: Number(t) })
    if (/^[A-Za-z_]/.test(t)) {
      if (peek() === '(') {
        take()
        const args = []
        if (peek() !== ')') { do { args.push(ternary(depth + 1)) } while (peek() === ',' && take()) }
        if (take() !== ')') fail('EXPR_SYNTAX', `missing ) after ${t}(`)
        const f = Object.hasOwn(EXPR_FUNCTIONS, t) ? EXPR_FUNCTIONS[t] : null
        if (!f) fail('EXPR_UNKNOWN_FUNCTION', `unknown function ${t}()`, { name: t })
        if (args.length !== f.arity) fail('EXPR_ARITY', `${t}() takes ${f.arity} argument(s), got ${args.length}`, { name: t, expected: f.arity, got: args.length })
        return node({ k: 'call', name: t, args })
      }
      if (Object.hasOwn(EXPR_CONSTANTS, t)) return node({ k: 'num', v: EXPR_CONSTANTS[t] })
      if (!legal.has(t)) fail('EXPR_UNKNOWN_NAME', `unknown name ${JSON.stringify(t)}`, { name: t, legal: [...legal] })
      return node({ k: 'var', name: t })
    }
    fail('EXPR_SYNTAX', `unexpected token ${JSON.stringify(t)}`, { token: t })
  }

  function power(depth) {
    const base = primary(depth)
    if (peek() === '^' || peek() === '**') { take(); return node({ k: 'bin', op: '^', a: base, b: power(depth + 1) }) }
    return base
  }
  const LEVELS = [['*', '/', '%'], ['+', '-'], ['<', '<=', '>', '>='], ['==', '!=']]
  function binary(level, depth) {
    if (level < 0) return power(depth)
    let left = binary(level - 1, depth)
    while (LEVELS[level].includes(peek())) { const op = take(); left = node({ k: 'bin', op, a: left, b: binary(level - 1, depth + 1) }) }
    return left
  }
  function ternary(depth) {
    const cond = binary(LEVELS.length - 1, depth)
    if (peek() !== '?') return cond
    take()
    const a = ternary(depth + 1)
    if (take() !== ':') fail('EXPR_SYNTAX', 'missing : in ?: expression')
    return node({ k: 'cond', cond, a, b: ternary(depth + 1) })
  }

  const ast = ternary(0)
  if (pos !== tokens.length) fail('EXPR_SYNTAX', `unexpected trailing ${JSON.stringify(tokens[pos])}`, { token: tokens[pos] })
  return { ast, nodeCount: count }
}

/** Evaluate a parsed AST against a plain {name: number} scope. */
export function evalExpr(ast, scope = {}, { checkFinite = true } = {}) {
  const walk = n => {
    switch (n.k) {
      case 'num': return n.v
      case 'var': return Object.hasOwn(scope, n.name) ? scope[n.name] : 0
      case 'neg': return -walk(n.a)
      case 'call': return EXPR_FUNCTIONS[n.name].fn(...n.args.map(walk))
      case 'cond': return walk(n.cond) ? walk(n.a) : walk(n.b)
      case 'bin': {
        const a = walk(n.a), b = walk(n.b)
        switch (n.op) {
          case '+': return a + b
          case '-': return a - b
          case '*': return a * b
          // Division by zero is refused, not returned as Infinity. IEEE-754 is right and useless
          // here: an Infinity spreads through the field and surfaces as a black tile three nodes
          // later, with nothing pointing back at the division.
          case '/': if (b === 0) fail('EXPR_DIVIDE_BY_ZERO', 'division by zero'); return a / b
          case '%': if (b === 0) fail('EXPR_DIVIDE_BY_ZERO', 'modulo by zero'); return a % b
          case '^': return Math.pow(a, b)
          case '<': return a < b ? 1 : 0
          case '<=': return a <= b ? 1 : 0
          case '>': return a > b ? 1 : 0
          case '>=': return a >= b ? 1 : 0
          case '==': return a === b ? 1 : 0
          case '!=': return a !== b ? 1 : 0
          default: fail('EXPR_SYNTAX', `unknown operator ${n.op}`)
        }
      }
      default: fail('EXPR_SYNTAX', `unknown node ${n.k}`)
    }
  }
  const v = walk(ast)
  if (checkFinite && !Number.isFinite(v)) fail('EXPR_NOT_FINITE', `expression produced ${String(v)}`, { value: String(v) })
  return v
}
