#!/bin/sh
# One gauntlet gate = one suite. Silent on pass, because the gate contract reads
# ANY stdout as a failure; on a failure it prints the summary line and the FAIL
# rows, which is what a critic would otherwise have been bought to discover.
#
#   $1  the validate script to run, relative to terrain-renderer/reference-impl
#
# Exit code is the suite's own -- both suites already exit non-zero on a FAIL, so
# the wrapper adds no judgement of its own. It only decides what reaches stdout.
set -e
root=$(git rev-parse --show-toplevel)
log=$(mktemp)
trap 'rm -f "$log"' EXIT
if (cd "$root/terrain-renderer/reference-impl" && python3 "$1" >"$log" 2>&1); then
    exit 0
fi
tail -n 3 "$log"
grep -E '\bFAIL\b|\bERROR\b' "$log" | head -n 25
exit 1
