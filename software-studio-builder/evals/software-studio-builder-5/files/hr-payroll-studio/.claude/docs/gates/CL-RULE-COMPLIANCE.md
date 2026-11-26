# CL-RULE-COMPLIANCE

**Agent**: `compliance-lead`  
**Phase**: requirements  
**Lean**: no  
**Trigger**: A rule catalog is written or changed  
**Context to pass**: The rule catalog and its sources  
**Verdicts**: COMPLIANT / CONCERNS / NON-COMPLIANT

Verdict words are ordered best first; the last is the failing word.

## Prompt

Does every rule cite its legal source and effective date, and does it respect personal-data rules?

## How to answer

Begin with `CL-RULE-COMPLIANCE: <word>` on its own line, using only the words above — or `CL-RULE-COMPLIANCE: NOT ASSESSED` when an input this gate names was not given to you or could not be read; name that input. A problem you did find takes the gate's own word, and so does an artifact the calling skill reports as absent: a missing artifact is a finding, not a missing input.
