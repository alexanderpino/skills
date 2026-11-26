# QL-UAT-SIGNOFF

**Agent**: `qa-lead`  
**Phase**: acceptance  
**Lean**: yes  
**Trigger**: UAT is complete  
**Context to pass**: The UAT report and open defects  
**Verdicts**: ACCEPT / CONCERNS / REJECT

Verdict words are ordered best first; the last is the failing word.

## Prompt

Did business users accept the release against its acceptance criteria?

## How to answer

Begin with `QL-UAT-SIGNOFF: <word>` on its own line, using only the words above — or `QL-UAT-SIGNOFF: NOT ASSESSED` when an input this gate names was not given to you or could not be read; name that input. A problem you did find takes the gate's own word, and so does an artifact the calling skill reports as absent: a missing artifact is a finding, not a missing input.
