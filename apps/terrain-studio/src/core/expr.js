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
//
// UNITS are the fourth bound, and they are checked ONCE at parse time rather than per sample, for
// the same reason the AST is built once: a 4096-square field is 16.7 million evaluations, and a
// property of the expression is not a property of the sample.
import { UNITS } from './ports.js'

// The parse-time bounds live in a RECORD the parser reads, and the two exported constants are the
// published snapshot of it (legacy.js republishes those through PORTS_EXPR for the bridge). Both
// are set from the same literal, so they cannot be written to disagree by accident.
//
// The record is writable ON PURPOSE: a limit that has never been seen not to fire is not a limit,
// and an oracle can only demonstrate that by raising it and watching production stop refusing. It
// is not a weakening of what "safe" means here — the threat is the EXPRESSION, and the grammar has
// no property access, no assignment and no way to name this object. Anything that can reach it
// already shares a realm with the whole app.
export const EXPR_LIMITS = Object.seal({ maxNodes: 256, maxDepth: 32 })
export const EXPR_MAX_NODES = EXPR_LIMITS.maxNodes
export const EXPR_MAX_DEPTH = EXPR_LIMITS.maxDepth

export const EXPR_UNIT_NONE = 'none'

// ---------------------------------------------------------------------------------------------
// UNIT SEMANTICS — measured against ports.js, not invented here.
//
// 1. COMPATIBILITY IS IDENTITY. ports.js note 2 settled this for the wire: ADR-002 says both
//    "dimensionally equal units" and "There are no implicit ... unit conversions", and identity is
//    the only reading under which rad->deg and degC->K are refused. `UNITS[u].dim` is recorded for
//    a future EXPLICIT converter and canConnect does not consult it. Neither does anything below —
//    if the grammar compared dimensions it would perform inside one Math node exactly the implicit
//    conversion the connection matrix refuses at the wire, and a user would reasonably conclude
//    that one of the two was broken.
//
// 2. THE VOCABULARY IS ports.js's UNITS, imported rather than restated. variables.js's
//    VARIABLE_UNITS is a subset of it (8 of the 11), and a variable is the only united value an
//    expression can name today, so an expression's units are a subset of a subset. A second list
//    here would drift; EXPR_UNIT_NAMES below is an index over the one list.
//
// 3. `none` IS THE MULTIPLICATIVE IDENTITY, NOT A WILDCARD. `2 * heightM` is metres — scaling by a
//    pure number is the one composition that needs no unit algebra. `heightM + 2` is REFUSED, and
//    that is the deliberate half: the grammar has no unit literal, so the `2` in that sum is a
//    number whose unit the author never stated, and admitting it under `+` is the "none means
//    whatever you like" rule that makes the whole check decorative. It is also precisely what
//    canConnect refuses when a `none` output meets an `m` input.
//
// 4. AN UNSTATED UNIT IS `none`, AND UNIT CHECKING IS THEREFORE INERT UNTIL A UNIT IS DECLARED.
//    Every policy below maps all-`none` operands to `none` without error, so no expression built
//    from literals, constants and undeclared names can raise a unit error. That is what makes this
//    safe to add to a shipped node: the Math node's three input ports declare `unit: 'none'`, so
//    every expression the app can evaluate today derives `none` and refuses nothing.
//
// 5. A COMPOSED UNIT IS REFUSED, NOT INVENTED. `m * m` has no name in UNITS (there is `m3`, no
//    `m2`), so it is EXPR_UNIT_UNREPRESENTABLE rather than silently `m` or silently `none`.
//    Cancellation is the exception and is allowed — `m / m` is `none` — because it needs no scale
//    factor and no new name. This is the seam where an explicit unit algebra would attach, the
//    same way `dim` is the seam for an explicit converter node.
//
// The unit of a name is supplied by the caller: `parseExpr(src, { names, units })`. The Math node
// builds that map from its input ports (all `none`) and the document variables in scope, each of
// which declares its unit — that declaration is the whole point of variables.js's `unit` field.

// A membership index over UNITS, derived at load. A unit name that does not exist at the wire does
// not exist in an expression: a typo'd unit is EXPR_UNIT_UNKNOWN rather than silently dimensionless,
// for the same reason a typo'd name is EXPR_UNKNOWN_NAME rather than silently 0.
export const EXPR_UNIT_NAMES = new Set(Object.keys(UNITS))

// Arity is declared so a wrong-arity call is a parse error rather than a silent undefined.
// `units` names the unit policy each function applies — see EXPR_UNIT_POLICIES. Declaring it in the
// same table as arity keeps one row per function: a function added without a unit policy is refused
// rather than silently waved through, which is the failure a table-driven design invites.
export const EXPR_FUNCTIONS = Object.freeze(Object.assign(Object.create(null), {
  abs: { arity: 1, fn: Math.abs, units: 'identity' }, min: { arity: 2, fn: Math.min, units: 'identity' }, max: { arity: 2, fn: Math.max, units: 'identity' },
  floor: { arity: 1, fn: Math.floor, units: 'identity' }, ceil: { arity: 1, fn: Math.ceil, units: 'identity' }, round: { arity: 1, fn: Math.round, units: 'identity' },
  sqrt: { arity: 1, fn: Math.sqrt, units: 'dimensionless' }, exp: { arity: 1, fn: Math.exp, units: 'dimensionless' }, log: { arity: 1, fn: Math.log, units: 'dimensionless' },
  // sin/cos/tan take an ANGLE, and `rad` is the only angle IEEE-754 trigonometry accepts. A `deg`
  // argument is refused rather than converted — the rad->deg refusal ports.js note 2 names, spelt
  // out inside the grammar. A bare number is radians, which is what Math.sin already means.
  sin: { arity: 1, fn: Math.sin, units: 'angleIn' }, cos: { arity: 1, fn: Math.cos, units: 'angleIn' }, tan: { arity: 1, fn: Math.tan, units: 'angleIn' },
  atan2: { arity: 2, fn: Math.atan2, units: 'angleOut' }, pow: { arity: 2, fn: Math.pow, units: 'dimensionless' },
  // A sign is a direction, not a length: sign(heightM) is dimensionless however united its input.
  sign: { arity: 1, fn: Math.sign, units: 'scalarize' },
  clamp: { arity: 3, fn: (v, lo, hi) => Math.min(Math.max(v, lo), hi), units: 'identity' },
  lerp: { arity: 3, fn: (a, b, t) => a + (b - a) * t, units: 'lerp' },
  // step is a 0/1 selector — the edge and the value must be comparable, the answer is a weight.
  step: { arity: 2, fn: (edge, v) => (v < edge ? 0 : 1), units: 'scalarize' },
}))

// The same table for operators. Written as data next to EXPR_FUNCTIONS rather than as conditionals
// buried in the walk, so the rule for `+` can be read, cited and — the reason it matters here —
// perturbed by an oracle to prove the check is load-bearing.
export const EXPR_OPERATOR_UNITS = Object.freeze(Object.assign(Object.create(null), {
  '+': { policy: 'identity' }, '-': { policy: 'identity' }, '%': { policy: 'identity' },
  '*': { policy: 'scale' }, '/': { policy: 'ratio' }, '^': { policy: 'dimensionless' },
  '<': { policy: 'scalarize' }, '<=': { policy: 'scalarize' }, '>': { policy: 'scalarize' },
  '>=': { policy: 'scalarize' }, '==': { policy: 'scalarize' }, '!=': { policy: 'scalarize' },
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
  // Four distinct unit failures, because they need four distinct fixes:
  //   MISMATCH        two operands that must agree do not      — degC + m
  //   DOMAIN          this position requires a particular unit — sin(deg), lerp(a, b, tInMetres)
  //   UNREPRESENTABLE the result has no name in the vocabulary — m * m, 1 / m
  //   UNKNOWN         the caller declared a unit UNITS has not — a typo, or drift from ports.js
  'EXPR_UNIT_MISMATCH', 'EXPR_UNIT_DOMAIN', 'EXPR_UNIT_UNREPRESENTABLE', 'EXPR_UNIT_UNKNOWN',
])

export class ExprError extends Error {
  constructor(code, message, detail) { super(message); this.name = 'ExprError'; this.code = code; this.detail = detail }
}
const fail = (code, message, detail) => { throw new ExprError(code, message, detail) }

// --- unit policies ---------------------------------------------------------------------------
// Each takes the operand units in order and returns the unit of the result, or fails. Every one of
// them maps all-`none` to `none` without error — invariant 4 above, and the reason this can be
// added to a node that already ships.
const NONE = EXPR_UNIT_NONE
const listUnits = us => us.join(', ')
const agree = (us, where) => {
  for (const u of us) {
    if (u !== us[0]) {
      fail('EXPR_UNIT_MISMATCH', `${where} needs matching units; got ${listUnits(us)} — there are no implicit unit conversions`, { where, units: us.slice() })
    }
  }
  return us[0]
}
export const EXPR_UNIT_POLICIES = Object.freeze(Object.assign(Object.create(null), {
  // Additive and order-preserving: operands identical, result that unit. m + m is m; m + none is a
  // refusal, because the grammar has no unit literal to make the `none` mean metres.
  identity: (us, where) => agree(us, where),
  // Comparable in, dimensionless out: a sign, a 0/1 selector, a comparison.
  scalarize: (us, where) => { agree(us, where); return NONE },
  // Multiplication. Scaling by a pure number keeps the unit; a genuine product has no name.
  scale: (us, where) => {
    const [a, b] = us
    if (a === NONE) return b
    if (b === NONE) return a
    fail('EXPR_UNIT_UNREPRESENTABLE', `${where} would produce ${a}*${b}, which UNITS cannot name`, { where, units: us.slice() })
  },
  // Division. Cancellation is exact and needs no new name; a reciprocal or a genuine quotient does.
  ratio: (us, where) => {
    const [a, b] = us
    if (b === NONE) return a
    if (a === b) return NONE
    fail('EXPR_UNIT_UNREPRESENTABLE', `${where} would produce ${a}/${b}, which UNITS cannot name`, { where, units: us.slice() })
  },
  // exp, log, sqrt, pow: the argument of a transcendental is a pure number. sqrt(m) is m^0.5 and
  // pow(m, 2) is m^2 — both unnameable — so the requirement is stated on the way in rather than
  // discovered on the way out.
  dimensionless: (us, where) => {
    for (const u of us) if (u !== NONE) fail('EXPR_UNIT_DOMAIN', `${where} requires dimensionless operands; got ${listUnits(us)}`, { where, units: us.slice() })
    return NONE
  },
  angleIn: (us, where) => {
    for (const u of us) {
      if (u !== NONE && u !== 'rad') fail('EXPR_UNIT_DOMAIN', `${where} takes radians; got ${u} — convert explicitly, there are no implicit unit conversions`, { where, units: us.slice() })
    }
    return NONE
  },
  // atan2 of two lengths is an angle. Of two pure numbers it is a pure number: staying dimensionless
  // when nothing declared a unit is invariant 4, and without it `atan2(a, b) + 0.5` would start
  // failing in expressions that carry no units at all.
  angleOut: (us, where) => (agree(us, where) === NONE ? NONE : 'rad'),
  // lerp(a, b, t): the endpoints must agree, the blend weight is a weight.
  lerp: (us, where) => {
    if (us[2] !== NONE) fail('EXPR_UNIT_DOMAIN', `${where} takes a dimensionless blend factor; got ${us[2]}`, { where, units: us.slice() })
    return agree([us[0], us[1]], where)
  },
}))

const applyUnitPolicy = (policy, us, where) => {
  const rule = policy && Object.hasOwn(EXPR_UNIT_POLICIES, policy) ? EXPR_UNIT_POLICIES[policy] : null
  // An unknown or missing policy is REFUSED, not ignored. The failure this catches is a function or
  // operator added to the tables above without a unit rule: waving it through would make the whole
  // check silently partial, and partial is the shape a vacuous gate hides in.
  if (!rule) fail('EXPR_UNIT_DOMAIN', `${where} declares no unit policy${policy ? ` (${JSON.stringify(policy)} is not one)` : ''}`, { where, policy: policy || null })
  return rule(us, where)
}

/**
 * The unit of a parsed expression, or a named failure. `units` maps name -> unit; a name that is
 * not in the map is dimensionless. Pure — it reads the AST and the map, and never the values.
 */
export function unitOfExpr(ast, units = {}) {
  for (const [name, unit] of Object.entries(units || {})) {
    if (!EXPR_UNIT_NAMES.has(unit)) {
      fail('EXPR_UNIT_UNKNOWN', `unknown unit ${JSON.stringify(unit)} declared for ${JSON.stringify(name)}`, { name, unit, known: [...EXPR_UNIT_NAMES] })
    }
  }
  const walk = n => {
    switch (n.k) {
      // A literal and a constant are pure numbers. `pi` is not radians: it is 3.14159, and sin()
      // accepts it because a bare number IS radians there.
      case 'num': return NONE
      case 'var': return (units && Object.hasOwn(units, n.name)) ? units[n.name] : NONE
      case 'neg': return walk(n.a)
      case 'call': return applyUnitPolicy(EXPR_FUNCTIONS[n.name].units, n.args.map(walk), `${n.name}()`)
      case 'cond': {
        // A condition is a truth value, which is dimensionless; the branches are the result, so
        // they must agree with each other exactly as the two sides of a `+` must.
        const c = walk(n.cond)
        if (c !== NONE) fail('EXPR_UNIT_DOMAIN', `the condition of ?: is a truth value and must be dimensionless; got ${c}`, { where: '?:', units: [c] })
        return applyUnitPolicy('identity', [walk(n.a), walk(n.b)], 'the branches of ?:')
      }
      case 'bin': {
        const rule = Object.hasOwn(EXPR_OPERATOR_UNITS, n.op) ? EXPR_OPERATOR_UNITS[n.op] : null
        return applyUnitPolicy(rule ? rule.policy : null, [walk(n.a), walk(n.b)], `operator ${n.op}`)
      }
      default: fail('EXPR_SYNTAX', `unknown node ${n.k}`)
    }
  }
  return walk(ast)
}

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
 * `units` maps those names to their declared units; an unlisted name is dimensionless, so a caller
 * that knows nothing about units gets exactly the pre-unit behaviour.
 *
 * Returns { ast, nodeCount, unit } — the unit of the whole expression, derived once here rather
 * than per sample, because it is a property of the program and not of the number.
 */
export function parseExpr(src, { names = [], units = {} } = {}) {
  const tokens = tokenize(String(src == null ? '' : src))
  if (!tokens.length) fail('EXPR_SYNTAX', 'empty expression')
  const legal = new Set(names)
  let pos = 0, count = 0
  const peek = () => tokens[pos]
  const take = () => tokens[pos++]
  const node = n => { if (++count > EXPR_LIMITS.maxNodes) fail('EXPR_TOO_LARGE', `expression exceeds ${EXPR_LIMITS.maxNodes} nodes`, { limit: EXPR_LIMITS.maxNodes }); return n }

  function primary(depth) {
    if (depth > EXPR_LIMITS.maxDepth) fail('EXPR_TOO_DEEP', `expression nests deeper than ${EXPR_LIMITS.maxDepth}`, { limit: EXPR_LIMITS.maxDepth })
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
  return { ast, nodeCount: count, unit: unitOfExpr(ast, units) }
}

/**
 * Evaluate a parsed AST against a plain {name: number} scope.
 * Units are deliberately ABSENT here: they were settled at parse time and a sample is a float. A
 * per-sample unit check would cost 16.7 million redundant decisions on a 4096-square field and
 * could not answer anything the parse did not already answer.
 */
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
