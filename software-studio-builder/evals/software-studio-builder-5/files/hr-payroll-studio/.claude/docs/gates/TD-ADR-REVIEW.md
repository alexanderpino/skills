# TD-ADR-REVIEW

**Agent**: `technical-director`  
**Phase**: architecture  
**Lean**: yes  
**Trigger**: An ADR is proposed  
**Context to pass**: The ADR and related ADRs  
**Verdicts**: APPROVE / CONCERNS / REJECT

Verdict words are ordered best first; the last is the failing word.

## Prompt

Is the decision sound, are alternatives fair, and do consequences cover security and data?

## How to answer

Begin with `TD-ADR-REVIEW: <word>` on its own line, using only the words above — or `TD-ADR-REVIEW: NOT ASSESSED` when an input this gate names was not given to you or could not be read; name that input. A problem you did find takes the gate's own word, and so does an artifact the calling skill reports as absent: a missing artifact is a finding, not a missing input.
