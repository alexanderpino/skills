#!/usr/bin/env bash
# PreToolUse(Bash): before `git commit`, check staged JSON parses and staged specs keep their
# required headings. Warns, never blocks. Exits at once for any other command.
. "$(dirname "$0")/_common.sh"
HOOK_INPUT="$(cat)"
CMD="$(json_field tool_input.command)"
case "$CMD" in *"git commit"*) ;; *) exit 0 ;; esac
ROOT="$(studio_root)"
cd "$ROOT" 2>/dev/null || exit 0
command -v python3 >/dev/null 2>&1 || { warn "validate-commit: python3 not found — staged files NOT ASSESSED"; exit 0; }
MSGS=""
for f in $(git diff --cached --name-only --diff-filter=ACM 2>/dev/null); do
  case "$f" in
    *.json)
      python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$f" 2>/dev/null || MSGS="$MSGS invalid JSON: $f;" ;;
    docs/specs/*.md)
      for h in "## Overview" "## Acceptance Criteria"; do
        grep -qF "$h" "$f" || MSGS="$MSGS $f lacks '$h';"
      done ;;
  esac
  case "$f" in
    *.md|*.json|*.yaml) ;;
    *) git diff --cached -U0 -- "$f" 2>/dev/null | grep -E '^\+.*TODO([^(]|$)' >/dev/null 2>&1 \
         && MSGS="$MSGS $f adds a TODO without an owner, e.g. TODO(name):;" ;;
  esac
done
[ -n "$MSGS" ] && warn "validate-commit:$MSGS"
exit 0
