#!/usr/bin/env bash
# SubagentStart / SubagentStop: append one line per event to the agent audit trail.
. "$(dirname "$0")/_common.sh"
HOOK_INPUT="$(cat)"
ROOT="$(studio_root)"
mkdir -p "$ROOT/production/session-logs" 2>/dev/null || exit 0
EVENT="$(json_field hook_event_name)"
AGENT="$(json_field agent_type)"
printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${EVENT:-unknown}" "${AGENT:-unknown}" \
  >> "$ROOT/production/session-logs/agents.tsv" 2>/dev/null
exit 0
