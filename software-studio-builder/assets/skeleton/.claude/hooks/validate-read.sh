#!/usr/bin/env bash
# PreToolUse(Read): refuse a whole-file read of a long document and answer with its headings,
# so the retry reads one section (offset/limit). The only hook that refuses, and it says why.
. "$(dirname "$0")/_common.sh"
HOOK_INPUT="$(cat)"
FILE="$(json_field tool_input.file_path)"
LIMIT="$(json_field tool_input.limit)"
OFFSET="$(json_field tool_input.offset)"
[ -z "$FILE" ] && exit 0
[ -n "$LIMIT$OFFSET" ] && exit 0
case "$FILE" in *.md) ;; *) exit 0 ;; esac
case "$FILE" in */docs/*|*/design/*) ;; *) exit 0 ;; esac
[ -f "$FILE" ] || exit 0
SIZE=$(wc -c < "$FILE" 2>/dev/null || echo 0)
[ "$SIZE" -le 40000 ] && exit 0
{
  echo "validate-read: $FILE is $SIZE bytes (over 40 KB). Read the section you need with offset and limit."
  echo "Headings (line: heading):"
  grep -n '^#' "$FILE" | head -80
} >&2
exit 2
