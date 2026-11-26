#!/usr/bin/env bash
# Shared helpers for the studio's hooks. Sourced, never run on its own.
# Hooks warn and never rewrite input; only validate-read.sh refuses (exit 2), and it says why.

studio_root() {
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then printf '%s' "$CLAUDE_PROJECT_DIR"; else pwd; fi
}

# json_field <dotted.path> — read one field from the hook's JSON on stdin (cached in $HOOK_INPUT).
json_field() {
  command -v python3 >/dev/null 2>&1 || { printf ''; return 0; }
  printf '%s' "$HOOK_INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for k in sys.argv[1].split("."):
    d = d.get(k) if isinstance(d, dict) else None
print("" if d is None else d)' "$1" 2>/dev/null
}

# warn <message> — surface a warning to the user without blocking the tool call.
warn() {
  command -v python3 >/dev/null 2>&1 || { printf '%s\n' "$1" >&2; return 0; }
  python3 -c 'import json,sys; print(json.dumps({"systemMessage": sys.argv[1]}))' "$1"
}
