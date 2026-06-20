#!/usr/bin/env bash
# driver.sh — smoke test for the architecture-docs CI tooling (arch_lint.py +
# detect_doc_conventions.py). It does NOT lint this repo; it builds throwaway
# fixture docs trees in a temp dir and proves the validator:
#   1. PASSES (exit 0) on a conformant ISO/IEC/IEEE 42010 docs tree,
#   2. FAILS  (exit 1) on a deliberately broken one (the part that matters —
#      a validator that never fails is worthless), catching the seeded errors,
#   3. and that the house-style detector emits a profile arch_lint can enforce.
#
# Usage (paths relative to architecture-docs/, the unit root):
#   bash .claude/skills/run-architecture-docs-ci/driver.sh
# Exit 0 = all assertions held; non-zero = the tooling regressed.
set -u

# Resolve the tools relative to this script, so it runs from anywhere.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT="$(cd "$HERE/../../.." && pwd)"          # architecture-docs/
TOOLS="$UNIT/assets/ci/tools"
LINT="$TOOLS/arch_lint.py"
DETECT="$TOOLS/detect_doc_conventions.py"
PY="${PYTHON:-python3}"

# Portable sed -i wrapper for macOS/Linux compatibility
sedi() {
  if [ "$(uname)" = "Darwin" ]; then
    sed -i "" "$@"
  else
    sed -i "$@"
  fi
}

pass=0; fail=0
ok()   { echo "  PASS: $1"; pass=$((pass+1)); }
bad()  { echo "  FAIL: $1"; fail=$((fail+1)); }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
ROOT="$WORK/docs/architecture"
mkdir -p "$ROOT/decisions/rfc" "$ROOT/software" "$WORK/src"

# ---------- GOOD fixture: a minimal but 42010-conformant docs tree ----------
cat > "$ROOT/README.md" <<'EOF'
---
id: architecture-index
title: Architecture docs index
---
# Architecture docs
EOF

cat > "$ROOT/AD.md" <<'EOF'
---
id: AD
title: Demo — Architecture Description
status: current
level: software
updated: 2026-06-20
---
# Architecture Description — Demo

## 2. Stakeholders
| ID | Stakeholder | Concerns |
|----|-------------|----------|
| SH.01 | Developer | CN.01 |

## 3. Concerns
| ID | Concern | Framed by |
|----|---------|-----------|
| CN.01 | How do I integrate the system? | VP-CTX |

## 5. Viewpoint catalogue
| Viewpoint | Name | Governs |
|-----------|------|---------|
| VP-CTX | Context | V-CTX |

## 6. Views
| View | Governing viewpoint | Realized in |
|------|---------------------|-------------|
| V-CTX | VP-CTX | HLD section 2 |

## 7. Correspondences & consistency
Known inconsistencies: none.

## 8. Decisions
See decisions/.
EOF

cat > "$ROOT/conformance-checklist.md" <<'EOF'
---
id: conformance-checklist
title: ISO conformance checklist
status: current
updated: 2026-06-20
---
# ISO conformance checklist
Every required item is satisfied.
EOF

cat > "$ROOT/software/HLD.md" <<'EOF'
---
id: HLD
title: Demo HLD
status: current
level: software
updated: 2026-06-20
security-reviewed: true
cost-reviewed: true
---
# HLD — Demo
## 8. Security — threat model
STRIDE mapped to OWASP Top 10:2025.
## 9. FinOps — cost estimate
Infracost cost estimate matrix.
EOF

cat > "$ROOT/decisions/ADR-0001-demo.md" <<'EOF'
---
id: ADR-0001
title: Use a file-based event bus
status: accepted
level: software
date: 2026-06-20
---
# ADR-0001: Use a file-based event bus
## Status
Accepted
## Context
The forces at play.
## Decision
We will use a file-based event bus.
## Consequences
Trade-offs recorded here.
EOF

cat > "$ROOT/decisions/rfc/RFC-0001-demo.md" <<'EOF'
---
id: RFC-0001
title: Proposal for the event bus
status: in-review
level: software
date: 2026-06-20
---
# RFC-0001: Proposal for the event bus
A proposal open for comment.
EOF

# A source file that enacts the decision (drift check).
cat > "$WORK/src/bus.py" <<'EOF'
# ARCH-REF: ADR-0001 (docs/architecture/decisions/ADR-0001-demo.md)
def publish(event): ...
EOF

echo "== 1. arch_lint on a CONFORMANT tree (expect exit 0) =="
"$PY" "$LINT" all --root "$ROOT" --src "$WORK/src"
rc=$?
[ "$rc" -eq 0 ] && ok "conformant tree passes (exit 0)" || bad "conformant tree should pass, got exit $rc"

echo "== 2. detect_doc_conventions emits a house profile (expect exit 0 + file) =="
PROFILE="$ROOT/house-profile.yaml"
"$PY" "$DETECT" --root "$ROOT" --repo-root "$WORK" --out "$PROFILE"
rc=$?
{ [ "$rc" -eq 0 ] && [ -s "$PROFILE" ]; } \
  && ok "house profile written ($PROFILE)" \
  || bad "detector should write a non-empty profile, got exit $rc"

echo "== 3. arch_lint enforces the detected house profile (expect exit 0) =="
"$PY" "$LINT" all --root "$ROOT" --src "$WORK/src" --house "$PROFILE"
rc=$?
[ "$rc" -eq 0 ] && ok "conformant tree passes under --house" || bad "house enforcement broke a clean tree, exit $rc"
rm -f "$PROFILE"   # remove so it isn't linted as a stray doc in step 4

# ---------- BREAK the tree deliberately and prove the gate catches it ----------
echo "== 4. arch_lint on a BROKEN tree (expect exit 1 + seeded errors) =="
# (a) concern framed by an unknown viewpoint (42010 conformance error)
sedi 's/VP-CTX | V-CTX/VP-GONE | V-CTX/' "$ROOT/AD.md" 2>/dev/null || true
sedi 's/| CN.01 | How do I integrate the system? | VP-CTX |/| CN.01 | How do I integrate the system? | VP-GONE |/' "$ROOT/AD.md"
# (b) RFC in an invalid status ('review' is not allowed; only 'in-review' is)
sedi 's/status: in-review/status: review/' "$ROOT/decisions/rfc/RFC-0001-demo.md"
# (c) ADR marked superseded but with no 'superseded-by' link
sedi 's/status: accepted/status: superseded/' "$ROOT/decisions/ADR-0001-demo.md"
# (d) an unresolved gap left in the conformance checklist
printf '\n| 1 | Stakeholders identified | \xe2\x9d\x8c | AD.md |\n' >> "$ROOT/conformance-checklist.md"

OUT="$("$PY" "$LINT" all --root "$ROOT" --src "$WORK/src" 2>&1)"
rc=$?
echo "$OUT" | sed 's/^/    | /'
[ "$rc" -ne 0 ] && ok "broken tree fails the gate (exit $rc)" || bad "broken tree should fail, got exit 0"
echo "$OUT" | grep -q "unknown viewpoint VP-GONE" && ok "caught unknown-viewpoint error" || bad "missed unknown-viewpoint error"
echo "$OUT" | grep -qi "invalid status 'review'" && ok "caught invalid RFC status" || bad "missed invalid RFC status"
echo "$OUT" | grep -qi "superseded ADR must set" && ok "caught dangling supersession" || bad "missed dangling supersession"
echo "$OUT" | grep -q "still has" && ok "caught unresolved conformance gap" || bad "missed unresolved checklist gap"

# ---------- the committed worked example must stay conformant ----------
echo "== 5. arch_lint on the committed worked example (expect exit 0) =="
EX="$UNIT/examples/brownfield-api-keys"
if [ -d "$EX/docs/architecture" ]; then
  EXOUT="$("$PY" "$LINT" all --root "$EX/docs/architecture" --src "$EX/src" 2>&1)"
  rc=$?
  echo "$EXOUT" | sed 's/^/    | /'
  { [ "$rc" -eq 0 ] && echo "$EXOUT" | grep -q "0 error"; } \
    && ok "worked example (given epic+FRs+ACs → docs) lints clean" \
    || bad "worked example regressed, exit $rc"
else
  bad "worked example missing at $EX"
fi

echo
echo "Summary: $pass passed, $fail failed."
[ "$fail" -eq 0 ] && { echo "DRIVER OK"; exit 0; } || { echo "DRIVER FAILED"; exit 1; }
