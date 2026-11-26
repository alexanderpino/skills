#!/usr/bin/env bash
# SessionStart: orient the session — branch, recent commits, the session checkpoint, config notes.
. "$(dirname "$0")/_common.sh"
HOOK_INPUT="$(cat)"
ROOT="$(studio_root)"
cd "$ROOT" 2>/dev/null || exit 0
echo "=== Studio session ==="
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "branch: $(git branch --show-current 2>/dev/null)"
  git log --oneline -5 2>/dev/null | sed 's/^/  /'
else
  echo "git: not a repository"
fi
if [ ! -f project.yaml ]; then
  echo "project.yaml is missing — run /start"
elif command -v python3 >/dev/null 2>&1; then
  python3 .claude/scripts/resolve_config.py --keys modes.rigor,project.stage,stack.name 2>/dev/null | sed 's/^/  /'
else
  echo "python3 not found — config cannot be resolved; every setting falls back to its default"
fi
if [ -f production/session-state/active.md ]; then
  echo "--- production/session-state/active.md (the checkpoint; read it before anything else) ---"
  tail -n 20 production/session-state/active.md
fi
exit 0
