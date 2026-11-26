# DD-RELEASE-READINESS

**Agent**: `delivery-director`  
**Phase**: build  
**Lean**: no  
**Trigger**: Leaving the build phase  
**Context to pass**: Open defects, test results, the UAT plan  
**Verdicts**: READY / CONCERNS / NOT READY

Verdict words are ordered best first; the last is the failing word.

## Prompt

Is the increment ready for acceptance testing?

## How to answer

Begin with `DD-RELEASE-READINESS: <word>` on its own line, using only the words above — or `DD-RELEASE-READINESS: NOT ASSESSED` when an input this gate names was not given to you or could not be read; name that input. A problem you did find takes the gate's own word, and so does an artifact the calling skill reports as absent: a missing artifact is a finding, not a missing input.
