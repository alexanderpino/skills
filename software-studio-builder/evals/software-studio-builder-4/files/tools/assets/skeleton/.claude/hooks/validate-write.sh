#!/usr/bin/env bash
# PreToolUse(Write|Edit): warn on writes the studio's rules say need care. Never blocks.
. "$(dirname "$0")/_common.sh"
HOOK_INPUT="$(cat)"
FILE="$(json_field tool_input.file_path)"
[ -z "$FILE" ] && exit 0
ROOT="$(studio_root)"
REL="${FILE#"$ROOT"/}"
case "$REL" in
  .env|.env.*|*/.env|*/.env.*|*/secrets/*)
    warn "validate-write: $REL looks like a secret file — keep secrets out of the repository" ;;
  .claude/settings.json)
    warn "validate-write: $REL holds the deny list and hooks — the change needs the user's explicit approval" ;;
  project.yaml|project.local.yaml)
    warn "validate-write: $REL changed — check it with: python3 .claude/scripts/resolve_config.py --validate" ;;
  docs/studio-research/*)
    warn "validate-write: $REL is the research record the template was built from — append, do not rewrite" ;;
esac
exit 0
